"""Instagram video crawler with rate limiting and error handling."""

import json
import logging
import random
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import instaloader
from instaloader.exceptions import (
    ConnectionException,
    QueryReturnedBadRequestException,
    TooManyRequestsException,
)
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Rate limiting constants - be conservative to avoid bans
BASE_DELAY_SECONDS = 5.0
DELAY_JITTER_SECONDS = 3.0
RATE_LIMIT_PAUSE_SECONDS = 120
MAX_RATE_LIMIT_RETRIES = 5


def _sleep_with_jitter(base: float = BASE_DELAY_SECONDS) -> None:
    """Sleep with random jitter to avoid detection patterns."""
    jitter = random.uniform(0, DELAY_JITTER_SECONDS)
    time.sleep(base + jitter)


class VideoPost(BaseModel):
    """Represents an Instagram video post."""

    shortcode: str
    url: str
    video_url: str
    caption: str | None = None


class VideoList(BaseModel):
    """List of videos from a profile."""

    profile: str
    videos: list[VideoPost]


def load_video_list(file_path: Path) -> VideoList:
    """Load video list from JSON file."""
    data = json.loads(file_path.read_text())
    return VideoList.model_validate(data)


def save_video_list(video_list: VideoList, file_path: Path) -> None:
    """Save video list to JSON file."""
    file_path.write_text(video_list.model_dump_json(indent=2))
    logger.info(f"Saved {len(video_list.videos)} videos to {file_path}")


class InstagramCrawler:
    """Crawls Instagram profiles for video posts with rate limiting."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the crawler. Tries session first, falls back to login."""
        self._loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern="",
            max_connection_attempts=3,
            request_timeout=30,
        )

        self._loader.context.sleep = True
        self._loader.context.max_connection_attempts = 3

        # Try to load existing session first
        if self._try_load_session(username):
            logger.info(f"Using existing session for {username}")
        else:
            logger.info(f"No valid session found, logging in as {username}...")
            self._loader.login(username, password)
            logger.info(f"Successfully logged in as {username}")

    def _try_load_session(self, username: str) -> bool:
        """Try to load session from default locations."""
        import glob
        import tempfile

        home = Path.home()
        possible_paths = [
            home / ".config" / "instaloader" / f"session-{username}",
            home / ".instaloader" / f"session-{username}",
            Path(tempfile.gettempdir()) / f"session-{username}",
        ]

        for session_path in possible_paths:
            if session_path.exists():
                try:
                    self._loader.load_session_from_file(
                        username=username, filename=str(session_path)
                    )
                    logger.info(f"Loaded session from {session_path}")
                    return True
                except Exception as e:
                    logger.debug(f"Failed to load session from {session_path}: {e}")

        # Also try wildcard match for any session
        wildcard_paths = [
            home / ".config" / "instaloader" / "session-*",
            home / ".instaloader" / "session-*",
        ]

        for pattern in wildcard_paths:
            matches = glob.glob(str(pattern))
            for match in matches:
                try:
                    session_username = Path(match).stem.replace("session-", "")
                    self._loader.load_session_from_file(
                        username=session_username, filename=match
                    )
                    logger.info(f"Loaded session from {match}")
                    return True
                except Exception as e:
                    logger.debug(f"Failed to load session from {match}: {e}")

        return False

    def _handle_rate_limit(self, attempt: int) -> bool:
        """Handle rate limit with exponential backoff."""
        if attempt >= MAX_RATE_LIMIT_RETRIES:
            logger.error(f"Max rate limit retries ({MAX_RATE_LIMIT_RETRIES}) exceeded")
            return False

        wait_time = RATE_LIMIT_PAUSE_SECONDS * (2**attempt)
        wait_time = min(wait_time, 600)
        logger.warning(
            f"Rate limited (attempt {attempt + 1}/{MAX_RATE_LIMIT_RETRIES}), "
            f"waiting {wait_time}s..."
        )
        time.sleep(wait_time)
        return True

    @retry(
        retry=retry_if_exception_type(
            (ConnectionException, QueryReturnedBadRequestException)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=60, min=60, max=300),
        before_sleep=lambda retry_state: logger.warning(
            f"Connection error, retrying in {retry_state.next_action.sleep}s..."
        ),
    )
    def _get_profile(self, profile_name: str) -> instaloader.Profile:
        """Get profile with retry logic."""
        _sleep_with_jitter(2)
        return instaloader.Profile.from_username(self._loader.context, profile_name)

    def list_videos(self, profile_name: str) -> VideoList:
        """Get all video posts from a profile.

        Returns a VideoList that can be saved to file.
        """
        logger.info(f"Fetching profile: {profile_name}")
        profile = self._get_profile(profile_name)
        logger.info(f"Profile has {profile.mediacount} posts")

        videos: list[VideoPost] = []
        rate_limit_attempts = 0
        post_iterator = profile.get_posts()
        seen_shortcodes: set[str] = set()

        while True:
            try:
                _sleep_with_jitter()
                post = next(post_iterator)
                rate_limit_attempts = 0

                if post.shortcode in seen_shortcodes:
                    continue
                seen_shortcodes.add(post.shortcode)

                if not post.is_video:
                    logger.debug(f"Skipping non-video: {post.shortcode}")
                    continue

                try:
                    video_url = self._get_video_url(post)
                    if video_url:
                        videos.append(
                            VideoPost(
                                shortcode=post.shortcode,
                                url=f"https://www.instagram.com/p/{post.shortcode}/",
                                video_url=video_url,
                                caption=post.caption,
                            )
                        )
                        logger.info(f"Found video {len(videos)}: {post.shortcode}")
                except Exception as e:
                    logger.error(f"Error getting video URL for {post.shortcode}: {e}")

            except StopIteration:
                break

            except (
                ConnectionException,
                QueryReturnedBadRequestException,
                TooManyRequestsException,
            ) as e:
                logger.warning(f"Rate limit or connection error: {e}")
                if not self._handle_rate_limit(rate_limit_attempts):
                    # Save what we have so far
                    logger.warning(f"Stopping early, collected {len(videos)} videos")
                    break
                rate_limit_attempts += 1
                post_iterator = profile.get_posts()
                # Skip already seen
                for _ in range(len(seen_shortcodes)):
                    try:
                        next(post_iterator)
                    except StopIteration:
                        break

        logger.info(f"Total videos found: {len(videos)}")
        return VideoList(profile=profile_name, videos=videos)

    def get_video_posts(
        self, profile_name: str, skip_shortcodes: set[str] | None = None
    ) -> Iterator[VideoPost]:
        """Iterate over video posts from a profile."""
        video_list = self.list_videos(profile_name)
        skip_shortcodes = skip_shortcodes or set()

        for video in video_list.videos:
            if video.shortcode not in skip_shortcodes:
                yield video

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=10, max=120),
    )
    def _get_video_url(self, post: instaloader.Post) -> str | None:
        """Get video URL from post with retry logic."""
        if post.typename == "GraphSidecar":
            for node in post.get_sidecar_nodes():
                if node.is_video:
                    return node.video_url
            return None
        return post.video_url

    @retry(
        retry=retry_if_exception_type(
            (ConnectionException, QueryReturnedBadRequestException)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=60, min=60, max=300),
    )
    def get_post_by_shortcode(self, shortcode: str) -> VideoPost | None:
        """Fetch a single post by shortcode and return VideoPost if it's a video."""
        _sleep_with_jitter(2)
        try:
            post = instaloader.Post.from_shortcode(self._loader.context, shortcode)
            if not post.is_video:
                logger.debug(f"Post {shortcode} is not a video")
                return None

            video_url = self._get_video_url(post)
            if not video_url:
                logger.debug(f"Could not get video URL for {shortcode}")
                return None

            return VideoPost(
                shortcode=shortcode,
                url=f"https://www.instagram.com/p/{shortcode}/",
                video_url=video_url,
                caption=post.caption,
            )
        except Exception as e:
            logger.warning(f"Failed to fetch post {shortcode}: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=5, max=60),
    )
    def download_video(self, video_url: str, output_path: Path) -> Path:
        """Download video to specified path."""
        logger.info(f"Downloading video to {output_path}")
        _sleep_with_jitter()
        urllib.request.urlretrieve(video_url, output_path)
        return output_path


def extract_shortcodes_from_html(html_path: Path) -> list[str]:
    """Extract Instagram post shortcodes from saved HTML page."""
    import re

    html = html_path.read_text(encoding="utf-8", errors="ignore")
    pattern = r"/(?:p|reel)/([A-Za-z0-9_-]{11})/"
    shortcodes = list(
        dict.fromkeys(re.findall(pattern, html))
    )  # Preserve order, dedupe
    logger.info(f"Extracted {len(shortcodes)} unique shortcodes from {html_path}")
    return shortcodes
