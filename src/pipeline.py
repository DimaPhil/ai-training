"""Main pipeline for processing Instagram profiles."""

import json
import logging
import tempfile
from pathlib import Path

from src.analyzer import VideoAnalyzer
from src.instagram import InstagramCrawler, VideoList, VideoPost
from src.models import ProgressState, VideoResult

logger = logging.getLogger(__name__)


def _get_progress_file(profile: str, output_dir: Path) -> Path:
    """Get the progress file path for a profile."""
    return output_dir / f".progress_{profile}.json"


def _get_results_file(profile: str, output_dir: Path) -> Path:
    """Get the results file path for a profile."""
    return output_dir / f"results_{profile}.jsonl"


def _load_progress(profile: str, output_dir: Path) -> ProgressState:
    """Load progress state from file or create new."""
    progress_file = _get_progress_file(profile, output_dir)
    results_file = _get_results_file(profile, output_dir)

    if progress_file.exists():
        try:
            data = json.loads(progress_file.read_text())
            state = ProgressState.model_validate(data)
            logger.info(
                f"Resuming from previous run. "
                f"Already processed: {len(state.processed_shortcodes)} videos"
            )
            return state
        except Exception as e:
            logger.warning(f"Failed to load progress file: {e}")

    return ProgressState(
        profile=profile,
        processed_shortcodes=[],
        results_file=str(results_file),
    )


def _save_progress(state: ProgressState, output_dir: Path) -> None:
    """Save progress state to file."""
    progress_file = _get_progress_file(state.profile, output_dir)
    progress_file.write_text(state.model_dump_json(indent=2))


def _append_result(result: VideoResult, results_file: Path) -> None:
    """Append a result to the JSONL output file."""
    with results_file.open("a") as f:
        f.write(result.model_dump_json() + "\n")


def _process_video(
    post: VideoPost,
    crawler: InstagramCrawler,
    analyzer: VideoAnalyzer,
) -> VideoResult:
    """Process a single video post."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = Path(tmp.name)

    try:
        logger.info(f"Processing video: {post.shortcode}")
        crawler.download_video(post.video_url, video_path)
        result = analyzer.analyze(video_path, post.shortcode)
        return result
    finally:
        if video_path.exists():
            video_path.unlink()
            logger.debug(f"Cleaned up video file: {video_path}")


def run_pipeline_from_file(
    video_list: VideoList,
    api_key: str,
    output_dir: Path,
    instagram_username: str,
    instagram_password: str,
    max_videos: int | None = None,
) -> None:
    """Run the analysis pipeline from a pre-fetched video list.

    Args:
        video_list: Pre-fetched list of videos.
        api_key: Google AI API key.
        output_dir: Directory for output files.
        instagram_username: Instagram login username.
        instagram_password: Instagram login password.
        max_videos: Optional limit on number of videos to process.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = video_list.profile
    state = _load_progress(profile, output_dir)
    results_file = Path(state.results_file)
    skip_shortcodes = set(state.processed_shortcodes)

    # Initialize components
    crawler = InstagramCrawler(username=instagram_username, password=instagram_password)
    analyzer = VideoAnalyzer(api_key=api_key)

    # Filter videos to process
    videos_to_process = [
        v for v in video_list.videos if v.shortcode not in skip_shortcodes
    ]

    if max_videos:
        videos_to_process = videos_to_process[:max_videos]

    logger.info(
        f"Processing {len(videos_to_process)} videos "
        f"(skipping {len(skip_shortcodes)} already processed)"
    )

    processed_count = 0
    error_count = 0

    try:
        for post in videos_to_process:
            try:
                result = _process_video(post, crawler, analyzer)

                # Only mark as processed if no error (so failed videos can be retried)
                if result.error:
                    error_count += 1
                    logger.warning(f"Video {post.shortcode} had error: {result.error}")
                    logger.info(
                        f"Video {post.shortcode} NOT marked as processed (will retry)"
                    )
                else:
                    _append_result(result, results_file)
                    state.processed_shortcodes.append(post.shortcode)
                    _save_progress(state, output_dir)
                    processed_count += 1

                    if result.is_exercise_video:
                        logger.info(f"Analyzed exercise video: {post.shortcode}")
                    else:
                        logger.info(f"Processed non-exercise video: {post.shortcode}")

            except Exception as e:
                logger.error(f"Failed to process {post.shortcode}: {e}")
                error_count += 1
                # Don't mark as processed - will retry next run
                logger.info(
                    f"Video {post.shortcode} NOT marked as processed (will retry)"
                )

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Progress saved.")
        raise

    finally:
        logger.info(
            f"Pipeline complete. Processed: {processed_count}, Errors: {error_count}"
        )
        logger.info(f"Results saved to: {results_file}")
