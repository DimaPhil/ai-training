"""Command-line interface for the Instagram training analyzer."""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.instagram import (
    InstagramCrawler,
    VideoList,
    VideoPost,
    load_video_list,
    save_video_list,
)
from src.pipeline import run_pipeline_from_file


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("instaloader").setLevel(logging.WARNING)


def cmd_list_videos(args: argparse.Namespace) -> None:
    """List videos from a profile and save to file."""
    logger = logging.getLogger(__name__)

    instagram_username = os.getenv("INSTAGRAM_USERNAME")
    instagram_password = os.getenv("INSTAGRAM_PASSWORD")
    if not instagram_username or not instagram_password:
        logger.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")
        sys.exit(1)

    output_file = args.output or Path(f"videos_{args.profile}.json")

    try:
        crawler = InstagramCrawler(
            username=instagram_username, password=instagram_password
        )
        video_list = crawler.list_videos(args.profile)
        save_video_list(video_list, output_file)
        logger.info(f"Saved {len(video_list.videos)} videos to {output_file}")
    except KeyboardInterrupt:
        logger.info("Aborted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Failed to list videos: {e}")
        sys.exit(1)


def cmd_parse_shortcodes(args: argparse.Namespace) -> None:
    """Parse shortcodes from JSON and fetch video URLs."""
    import json

    logger = logging.getLogger(__name__)

    instagram_username = os.getenv("INSTAGRAM_USERNAME")
    instagram_password = os.getenv("INSTAGRAM_PASSWORD")
    if not instagram_username or not instagram_password:
        logger.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")
        sys.exit(1)

    shortcodes_file = Path(args.shortcodes)
    if not shortcodes_file.exists():
        logger.error(f"Shortcodes file not found: {shortcodes_file}")
        sys.exit(1)

    shortcodes = json.loads(shortcodes_file.read_text())
    logger.info(f"Loaded {len(shortcodes)} shortcodes from {shortcodes_file}")

    output_file = args.output or Path(f"videos_{shortcodes_file.stem}.json")

    # Load existing progress if resuming
    existing_videos: list[VideoPost] = []
    processed_shortcodes: set[str] = set()
    if output_file.exists() and not args.fresh:
        try:
            existing = load_video_list(output_file)
            existing_videos = existing.videos
            processed_shortcodes = {v.shortcode for v in existing_videos}
            logger.info(f"Resuming: {len(processed_shortcodes)} already processed")
        except Exception as e:
            logger.warning(f"Could not load existing file: {e}")

    try:
        crawler = InstagramCrawler(
            username=instagram_username, password=instagram_password
        )

        videos = list(existing_videos)
        skipped = 0
        errors = 0

        for i, shortcode in enumerate(shortcodes):
            if shortcode in processed_shortcodes:
                continue

            logger.info(f"[{i + 1}/{len(shortcodes)}] Fetching {shortcode}...")
            try:
                video = crawler.get_post_by_shortcode(shortcode)
                if video:
                    videos.append(video)
                    logger.info(f"  Found video: {shortcode}")
                else:
                    skipped += 1
                    logger.debug(f"  Not a video: {shortcode}")

                # Save progress after each successful fetch
                video_list = VideoList(profile=args.profile or "unknown", videos=videos)
                save_video_list(video_list, output_file)

            except Exception as e:
                errors += 1
                logger.warning(f"  Error fetching {shortcode}: {e}")

        logger.info(f"Done: {len(videos)} videos, {skipped} skipped, {errors} errors")
        logger.info(f"Saved to {output_file}")

    except KeyboardInterrupt:
        logger.info("Aborted by user. Progress saved.")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Failed: {e}")
        sys.exit(1)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze videos from a previously saved list."""
    logger = logging.getLogger(__name__)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in .env")
        sys.exit(1)

    instagram_username = os.getenv("INSTAGRAM_USERNAME")
    instagram_password = os.getenv("INSTAGRAM_PASSWORD")
    if not instagram_username or not instagram_password:
        logger.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")
        sys.exit(1)

    video_list_file = Path(args.video_list)
    if not video_list_file.exists():
        logger.error(f"Video list file not found: {video_list_file}")
        sys.exit(1)

    try:
        video_list = load_video_list(video_list_file)
        logger.info(f"Loaded {len(video_list.videos)} videos from {video_list_file}")

        run_pipeline_from_file(
            video_list=video_list,
            api_key=api_key,
            output_dir=args.output,
            instagram_username=instagram_username,
            instagram_password=instagram_password,
            max_videos=args.max_videos,
        )
    except KeyboardInterrupt:
        logger.info("Aborted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze gym training videos from Instagram profiles"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to .env file (default: .env)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-videos command
    list_parser = subparsers.add_parser(
        "list-videos", help="List all videos from a profile and save to file"
    )
    list_parser.add_argument("profile", help="Instagram profile username")
    list_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON file (default: videos_<profile>.json)",
    )

    # parse-shortcodes command
    parse_parser = subparsers.add_parser(
        "parse-shortcodes",
        help="Fetch video URLs from a JSON array of shortcodes (from browser script)",
    )
    parse_parser.add_argument(
        "shortcodes", help="Path to JSON file with shortcode array"
    )
    parse_parser.add_argument(
        "-p",
        "--profile",
        help="Profile name for the output file (default: unknown)",
    )
    parse_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON file (default: videos_<shortcodes_filename>.json)",
    )
    parse_parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start fresh, ignore existing progress",
    )

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze videos from a saved list"
    )
    analyze_parser.add_argument("video_list", help="Path to video list JSON file")
    analyze_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for results (default: ./output)",
    )
    analyze_parser.add_argument(
        "-m",
        "--max-videos",
        type=int,
        help="Maximum number of videos to process",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.env_file.exists():
        load_dotenv(args.env_file)
        logging.getLogger(__name__).info(f"Loaded environment from: {args.env_file}")

    if args.command == "list-videos":
        cmd_list_videos(args)
    elif args.command == "parse-shortcodes":
        cmd_parse_shortcodes(args)
    elif args.command == "analyze":
        cmd_analyze(args)


if __name__ == "__main__":
    main()
