"""Tests for the analysis pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.instagram import VideoList, VideoPost
from src.models import ExerciseAnalysis, VideoResult
from src.pipeline import (
    _append_result,
    _get_progress_file,
    _get_results_file,
    _load_progress,
    _save_progress,
)


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_progress_file(self) -> None:
        """Test progress file path generation."""
        output_dir = Path("/tmp/test")
        path = _get_progress_file("test_profile", output_dir)
        assert path == Path("/tmp/test/.progress_test_profile.json")

    def test_get_results_file(self) -> None:
        """Test results file path generation."""
        output_dir = Path("/tmp/test")
        path = _get_results_file("test_profile", output_dir)
        assert path == Path("/tmp/test/results_test_profile.jsonl")


class TestProgressManagement:
    """Tests for progress state management."""

    def test_load_progress_new(self) -> None:
        """Test loading progress when no file exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            state = _load_progress("new_profile", output_dir)

            assert state.profile == "new_profile"
            assert state.processed_shortcodes == []
            assert "results_new_profile.jsonl" in state.results_file

    def test_load_progress_existing(self) -> None:
        """Test loading existing progress state."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            progress_file = output_dir / ".progress_test.json"

            # Write existing progress
            progress_data = {
                "profile": "test",
                "processed_shortcodes": ["A", "B", "C"],
                "results_file": "/some/path/results.jsonl",
            }
            progress_file.write_text(json.dumps(progress_data))

            state = _load_progress("test", output_dir)

            assert state.profile == "test"
            assert len(state.processed_shortcodes) == 3
            assert "A" in state.processed_shortcodes

    def test_load_progress_corrupted_file(self) -> None:
        """Test loading progress with corrupted file creates new state."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            progress_file = output_dir / ".progress_corrupted.json"
            progress_file.write_text("not valid json")

            state = _load_progress("corrupted", output_dir)

            # Should return fresh state
            assert state.profile == "corrupted"
            assert state.processed_shortcodes == []

    def test_save_progress(self) -> None:
        """Test saving progress state."""
        from src.models import ProgressState

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            state = ProgressState(
                profile="save_test",
                processed_shortcodes=["X", "Y", "Z"],
                results_file="/path/to/results.jsonl",
            )

            _save_progress(state, output_dir)

            progress_file = output_dir / ".progress_save_test.json"
            assert progress_file.exists()

            loaded = json.loads(progress_file.read_text())
            assert loaded["profile"] == "save_test"
            assert len(loaded["processed_shortcodes"]) == 3


class TestAppendResult:
    """Tests for result appending."""

    def test_append_result_new_file(self) -> None:
        """Test appending result to new file."""
        analysis = ExerciseAnalysis(
            muscle_group="chest",
            machine="bench",
            wrong_way="Bad form",
            correct_way="Good form",
            trainer_insights="Tips",
        )
        result = VideoResult(
            shortcode="NEW1",
            url="https://www.instagram.com/p/NEW1/",
            is_exercise_video=True,
            exercise_analysis=analysis,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            results_file = Path(f.name)

        try:
            _append_result(result, results_file)

            lines = results_file.read_text().strip().split("\n")
            assert len(lines) == 1

            parsed = VideoResult.model_validate_json(lines[0])
            assert parsed.shortcode == "NEW1"
        finally:
            results_file.unlink()

    def test_append_result_existing_file(self) -> None:
        """Test appending multiple results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            results_file = Path(f.name)

        try:
            for i in range(3):
                result = VideoResult(
                    shortcode=f"MULTI{i}",
                    url=f"https://www.instagram.com/p/MULTI{i}/",
                    is_exercise_video=False,
                    error="test error",
                )
                _append_result(result, results_file)

            lines = results_file.read_text().strip().split("\n")
            assert len(lines) == 3
        finally:
            results_file.unlink()


class TestRunPipeline:
    """Tests for the main pipeline function."""

    @patch("src.pipeline.InstagramCrawler")
    @patch("src.pipeline.VideoAnalyzer")
    def test_pipeline_processes_videos(
        self, mock_analyzer_class: MagicMock, mock_crawler_class: MagicMock
    ) -> None:
        """Test pipeline processes videos correctly."""
        from src.pipeline import run_pipeline_from_file

        # Setup mocks
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock analyzer to return results
        analysis = ExerciseAnalysis(
            muscle_group="back",
            machine="lat pulldown",
            wrong_way="Using momentum",
            correct_way="Slow and controlled",
            trainer_insights="Focus on squeeze",
        )
        mock_analyzer.analyze.return_value = VideoResult(
            shortcode="TEST1",
            url="https://www.instagram.com/p/TEST1/",
            is_exercise_video=True,
            exercise_analysis=analysis,
        )

        video_list = VideoList(
            profile="test_profile",
            videos=[
                VideoPost(
                    shortcode="TEST1",
                    url="https://www.instagram.com/p/TEST1/",
                    video_url="https://cdn.instagram.com/test1.mp4",
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            with patch("src.pipeline.tempfile.NamedTemporaryFile") as mock_tmp:
                # Mock temp file
                mock_tmp_file = MagicMock()
                mock_tmp_file.__enter__ = MagicMock(return_value=mock_tmp_file)
                mock_tmp_file.__exit__ = MagicMock(return_value=False)
                mock_tmp_file.name = "/tmp/fake_video.mp4"
                mock_tmp.return_value = mock_tmp_file

                with patch("src.pipeline.Path") as mock_path:
                    mock_video_path = MagicMock()
                    mock_video_path.exists.return_value = True
                    mock_path.return_value = mock_video_path

                    run_pipeline_from_file(
                        video_list=video_list,
                        api_key="test-key",
                        output_dir=output_dir,
                        instagram_username="user",
                        instagram_password="pass",
                        max_videos=1,
                    )

            # Check that crawler was initialized
            mock_crawler_class.assert_called_once_with(username="user", password="pass")

            # Check that analyzer was initialized
            mock_analyzer_class.assert_called_once_with(api_key="test-key")

    @patch("src.pipeline.InstagramCrawler")
    @patch("src.pipeline.VideoAnalyzer")
    def test_pipeline_skips_processed(
        self, mock_analyzer_class: MagicMock, mock_crawler_class: MagicMock
    ) -> None:
        """Test pipeline skips already processed videos."""
        from src.pipeline import run_pipeline_from_file

        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer

        video_list = VideoList(
            profile="skip_test",
            videos=[
                VideoPost(
                    shortcode="PROCESSED",
                    url="https://www.instagram.com/p/PROCESSED/",
                    video_url="https://cdn.instagram.com/processed.mp4",
                ),
                VideoPost(
                    shortcode="NEW",
                    url="https://www.instagram.com/p/NEW/",
                    video_url="https://cdn.instagram.com/new.mp4",
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            # Create existing progress
            progress_data = {
                "profile": "skip_test",
                "processed_shortcodes": ["PROCESSED"],
                "results_file": str(output_dir / "results_skip_test.jsonl"),
            }
            progress_file = output_dir / ".progress_skip_test.json"
            progress_file.write_text(json.dumps(progress_data))

            # Mock analyzer
            mock_analyzer.analyze.return_value = VideoResult(
                shortcode="NEW",
                url="https://www.instagram.com/p/NEW/",
                is_exercise_video=False,
                error="test",
            )

            with patch("src.pipeline.tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp_file = MagicMock()
                mock_tmp_file.__enter__ = MagicMock(return_value=mock_tmp_file)
                mock_tmp_file.__exit__ = MagicMock(return_value=False)
                mock_tmp_file.name = "/tmp/fake_video.mp4"
                mock_tmp.return_value = mock_tmp_file

                with patch("src.pipeline.Path") as mock_path:
                    mock_video_path = MagicMock()
                    mock_video_path.exists.return_value = True
                    mock_path.return_value = mock_video_path

                    run_pipeline_from_file(
                        video_list=video_list,
                        api_key="test-key",
                        output_dir=output_dir,
                        instagram_username="user",
                        instagram_password="pass",
                    )

            # Only NEW should be analyzed, PROCESSED should be skipped
            assert mock_analyzer.analyze.call_count == 1

    @patch("src.pipeline.InstagramCrawler")
    @patch("src.pipeline.VideoAnalyzer")
    def test_pipeline_respects_max_videos(
        self, mock_analyzer_class: MagicMock, mock_crawler_class: MagicMock
    ) -> None:
        """Test pipeline respects max_videos limit."""
        from src.pipeline import run_pipeline_from_file

        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer

        mock_analyzer.analyze.return_value = VideoResult(
            shortcode="X",
            url="https://www.instagram.com/p/X/",
            is_exercise_video=False,
            error="test",
        )

        video_list = VideoList(
            profile="max_test",
            videos=[
                VideoPost(
                    shortcode=f"VIDEO{i}",
                    url=f"https://www.instagram.com/p/VIDEO{i}/",
                    video_url=f"https://cdn.instagram.com/video{i}.mp4",
                )
                for i in range(10)
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            with patch("src.pipeline.tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp_file = MagicMock()
                mock_tmp_file.__enter__ = MagicMock(return_value=mock_tmp_file)
                mock_tmp_file.__exit__ = MagicMock(return_value=False)
                mock_tmp_file.name = "/tmp/fake_video.mp4"
                mock_tmp.return_value = mock_tmp_file

                with patch("src.pipeline.Path") as mock_path:
                    mock_video_path = MagicMock()
                    mock_video_path.exists.return_value = True
                    mock_path.return_value = mock_video_path

                    run_pipeline_from_file(
                        video_list=video_list,
                        api_key="test-key",
                        output_dir=output_dir,
                        instagram_username="user",
                        instagram_password="pass",
                        max_videos=3,
                    )

            # Should only process 3 videos
            assert mock_analyzer.analyze.call_count == 3
