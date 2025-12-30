"""Tests for the CLI module."""

import argparse
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cli import (
    cmd_analyze,
    cmd_list_videos,
    cmd_parse_shortcodes,
    main,
    setup_logging,
)


class TestSetupLogging:
    """Tests for logging setup."""

    def test_setup_logging_default(self) -> None:
        """Test default logging level is INFO."""
        # Reset root logger
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        root.setLevel(logging.WARNING)

        setup_logging(verbose=False)
        assert root.level == logging.INFO

    def test_setup_logging_verbose(self) -> None:
        """Test verbose logging sets DEBUG level."""
        # Reset root logger
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        root.setLevel(logging.WARNING)

        setup_logging(verbose=True)
        assert root.level == logging.DEBUG


class TestCmdListVideos:
    """Tests for list-videos command."""

    @patch("src.cli.InstagramCrawler")
    @patch("src.cli.save_video_list")
    @patch.dict(
        "os.environ", {"INSTAGRAM_USERNAME": "user", "INSTAGRAM_PASSWORD": "pass"}
    )
    def test_list_videos_success(
        self, mock_save: MagicMock, mock_crawler_class: MagicMock
    ) -> None:
        """Test successful video listing."""
        from src.instagram import VideoList, VideoPost

        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        mock_crawler.list_videos.return_value = VideoList(
            profile="test_profile",
            videos=[
                VideoPost(
                    shortcode="A",
                    url="https://www.instagram.com/p/A/",
                    video_url="https://cdn.instagram.com/a.mp4",
                )
            ],
        )

        args = argparse.Namespace(
            profile="test_profile",
            output=None,
        )

        cmd_list_videos(args)

        mock_crawler_class.assert_called_once_with(username="user", password="pass")
        mock_crawler.list_videos.assert_called_once_with("test_profile")
        mock_save.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_list_videos_missing_credentials(self) -> None:
        """Test error when credentials are missing."""
        args = argparse.Namespace(
            profile="test_profile",
            output=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_list_videos(args)

        assert exc_info.value.code == 1


class TestCmdParseShortcodes:
    """Tests for parse-shortcodes command."""

    @patch("src.cli.InstagramCrawler")
    @patch("src.cli.save_video_list")
    @patch.dict(
        "os.environ", {"INSTAGRAM_USERNAME": "user", "INSTAGRAM_PASSWORD": "pass"}
    )
    def test_parse_shortcodes_success(
        self, _mock_save: MagicMock, mock_crawler_class: MagicMock
    ) -> None:
        """Test successful shortcode parsing."""
        from src.instagram import VideoPost

        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        mock_crawler.get_post_by_shortcode.return_value = VideoPost(
            shortcode="SHORT1",
            url="https://www.instagram.com/p/SHORT1/",
            video_url="https://cdn.instagram.com/short1.mp4",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["SHORT1", "SHORT2"], f)
            shortcodes_file = Path(f.name)

        try:
            args = argparse.Namespace(
                shortcodes=str(shortcodes_file),
                profile="test_profile",
                output=None,
                fresh=False,
            )

            cmd_parse_shortcodes(args)

            mock_crawler.get_post_by_shortcode.assert_called()
        finally:
            shortcodes_file.unlink()

    @patch.dict("os.environ", {}, clear=True)
    def test_parse_shortcodes_missing_credentials(self) -> None:
        """Test error when credentials are missing."""
        args = argparse.Namespace(
            shortcodes="/fake/path.json",
            profile="test",
            output=None,
            fresh=False,
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_parse_shortcodes(args)

        assert exc_info.value.code == 1

    @patch.dict(
        "os.environ", {"INSTAGRAM_USERNAME": "user", "INSTAGRAM_PASSWORD": "pass"}
    )
    def test_parse_shortcodes_file_not_found(self) -> None:
        """Test error when shortcodes file doesn't exist."""
        args = argparse.Namespace(
            shortcodes="/nonexistent/file.json",
            profile="test",
            output=None,
            fresh=False,
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_parse_shortcodes(args)

        assert exc_info.value.code == 1


class TestCmdAnalyze:
    """Tests for analyze command."""

    @patch("src.cli.run_pipeline_from_file")
    @patch("src.cli.load_video_list")
    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test-key",
            "INSTAGRAM_USERNAME": "user",
            "INSTAGRAM_PASSWORD": "pass",
        },
    )
    def test_analyze_success(
        self, mock_load: MagicMock, mock_pipeline: MagicMock
    ) -> None:
        """Test successful analysis."""
        from src.instagram import VideoList, VideoPost

        mock_load.return_value = VideoList(
            profile="test",
            videos=[
                VideoPost(
                    shortcode="V1",
                    url="https://www.instagram.com/p/V1/",
                    video_url="https://cdn.instagram.com/v1.mp4",
                )
            ],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            video_list_file = Path(f.name)

        try:
            args = argparse.Namespace(
                video_list=str(video_list_file),
                output=Path("/tmp/output"),
                max_videos=None,
            )

            cmd_analyze(args)

            mock_load.assert_called_once()
            mock_pipeline.assert_called_once()
        finally:
            video_list_file.unlink()

    @patch.dict("os.environ", {}, clear=True)
    def test_analyze_missing_api_key(self) -> None:
        """Test error when API key is missing."""
        args = argparse.Namespace(
            video_list="/fake/path.json",
            output=Path("/tmp/output"),
            max_videos=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_analyze(args)

        assert exc_info.value.code == 1

    @patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "key", "INSTAGRAM_USERNAME": "", "INSTAGRAM_PASSWORD": ""},
    )
    def test_analyze_missing_instagram_credentials(self) -> None:
        """Test error when Instagram credentials are missing."""
        args = argparse.Namespace(
            video_list="/fake/path.json",
            output=Path("/tmp/output"),
            max_videos=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_analyze(args)

        assert exc_info.value.code == 1

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "key",
            "INSTAGRAM_USERNAME": "user",
            "INSTAGRAM_PASSWORD": "pass",
        },
    )
    def test_analyze_video_list_not_found(self) -> None:
        """Test error when video list file doesn't exist."""
        args = argparse.Namespace(
            video_list="/nonexistent/file.json",
            output=Path("/tmp/output"),
            max_videos=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_analyze(args)

        assert exc_info.value.code == 1


class TestMain:
    """Tests for main entry point."""

    @patch("src.cli.cmd_list_videos")
    @patch("src.cli.load_dotenv")
    @patch.dict(
        "os.environ", {"INSTAGRAM_USERNAME": "user", "INSTAGRAM_PASSWORD": "pass"}
    )
    def test_main_list_videos_command(
        self, _mock_dotenv: MagicMock, mock_cmd: MagicMock
    ) -> None:
        """Test main dispatches to list-videos command."""
        with (
            patch("sys.argv", ["cli", "list-videos", "test_profile"]),
            patch("src.cli.Path.exists", return_value=True),
        ):
            main()

        mock_cmd.assert_called_once()

    @patch("src.cli.cmd_parse_shortcodes")
    @patch("src.cli.load_dotenv")
    @patch.dict(
        "os.environ", {"INSTAGRAM_USERNAME": "user", "INSTAGRAM_PASSWORD": "pass"}
    )
    def test_main_parse_shortcodes_command(
        self, _mock_dotenv: MagicMock, mock_cmd: MagicMock
    ) -> None:
        """Test main dispatches to parse-shortcodes command."""
        with (
            patch("sys.argv", ["cli", "parse-shortcodes", "/path/to/shortcodes.json"]),
            patch("src.cli.Path.exists", return_value=True),
        ):
            main()

        mock_cmd.assert_called_once()

    @patch("src.cli.cmd_analyze")
    @patch("src.cli.load_dotenv")
    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "key",
            "INSTAGRAM_USERNAME": "user",
            "INSTAGRAM_PASSWORD": "pass",
        },
    )
    def test_main_analyze_command(
        self, _mock_dotenv: MagicMock, mock_cmd: MagicMock
    ) -> None:
        """Test main dispatches to analyze command."""
        with (
            patch("sys.argv", ["cli", "analyze", "/path/to/videos.json"]),
            patch("src.cli.Path.exists", return_value=True),
        ):
            main()

        mock_cmd.assert_called_once()

    @patch("src.cli.load_dotenv")
    def test_main_verbose_flag(self, _mock_dotenv: MagicMock) -> None:
        """Test verbose flag sets debug logging."""
        # Reset root logger
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        root.setLevel(logging.WARNING)

        with (
            patch("sys.argv", ["cli", "-v", "list-videos", "profile"]),
            patch("src.cli.Path.exists", return_value=True),
            patch("src.cli.cmd_list_videos"),
        ):
            main()

        assert root.level == logging.DEBUG

    def test_main_no_command(self) -> None:
        """Test main exits when no command provided."""
        with patch("sys.argv", ["cli"]), pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2  # argparse error
