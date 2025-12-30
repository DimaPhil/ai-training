"""Tests for Gemini video analyzer."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer import VideoAnalyzer, _load_prompt
from src.models import ExerciseAnalysis, GeneralInsights


class TestLoadPrompt:
    """Tests for prompt loading."""

    def test_load_prompt_returns_string(self) -> None:
        """Test that prompt is loaded successfully."""
        prompt = _load_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestVideoAnalyzer:
    """Tests for VideoAnalyzer class."""

    @patch("src.analyzer.genai.Client")
    def test_analyzer_initialization(self, mock_client_class: MagicMock) -> None:
        """Test analyzer initialization."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        analyzer = VideoAnalyzer(api_key="test-api-key")

        mock_client_class.assert_called_once_with(api_key="test-api-key")
        assert analyzer._client == mock_client

    @patch("src.analyzer.genai.Client")
    def test_analyze_exercise_video_success(self, mock_client_class: MagicMock) -> None:
        """Test successful analysis of an exercise video."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock file upload
        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"
        mock_file.name = "test-file"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file

        # Mock generate_content response
        mock_response = MagicMock()
        mock_response.text = ExerciseAnalysis(
            muscle_group="chest",
            machine="cable crossover",
            wrong_way="Arms too high",
            correct_way="Arms at shoulder height",
            trainer_insights="Focus on squeeze",
        ).model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        analyzer = VideoAnalyzer(api_key="test-key")

        # Create a temp video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            video_path = Path(f.name)

        try:
            with patch("src.analyzer.time.sleep"):
                result = analyzer.analyze(video_path, "TEST123")

            assert result.shortcode == "TEST123"
            assert result.is_exercise_video is True
            assert result.exercise_analysis is not None
            assert result.exercise_analysis.muscle_group == "chest"
            assert result.error is None
        finally:
            video_path.unlink()

    @patch("src.analyzer.genai.Client")
    def test_analyze_general_video_fallback(self, mock_client_class: MagicMock) -> None:
        """Test fallback to general insights when exercise schema fails."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock file upload
        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"
        mock_file.name = "test-file"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file

        # First call raises exception (exercise schema fails)
        # Second call returns general insights
        exercise_response = MagicMock()
        exercise_response.text = '{"invalid": "data"}'

        general_response = MagicMock()
        general_response.text = GeneralInsights(
            trainer_insights="Great motivation video",
            video_type="motivational content",
        ).model_dump_json()

        mock_client.models.generate_content.side_effect = [
            exercise_response,
            general_response,
        ]

        analyzer = VideoAnalyzer(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            video_path = Path(f.name)

        try:
            with patch("src.analyzer.time.sleep"):
                result = analyzer.analyze(video_path, "GENERAL1")

            assert result.shortcode == "GENERAL1"
            assert result.is_exercise_video is False
            assert result.general_insights is not None
            assert result.general_insights.video_type == "motivational content"
        finally:
            video_path.unlink()

    @patch("src.analyzer.genai.Client")
    def test_analyze_video_error_handling(self, mock_client_class: MagicMock) -> None:
        """Test error handling during video analysis."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock file upload to fail
        mock_client.files.upload.side_effect = Exception("Upload failed")

        analyzer = VideoAnalyzer(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            video_path = Path(f.name)

        try:
            with patch("src.analyzer.time.sleep"):
                result = analyzer.analyze(video_path, "ERROR1")

            assert result.shortcode == "ERROR1"
            assert result.is_exercise_video is False
            assert result.error is not None
            # Error could be wrapped in RetryError
            assert "Upload failed" in result.error or "RetryError" in result.error
        finally:
            video_path.unlink()

    @patch("src.analyzer.genai.Client")
    def test_delete_video_success(self, mock_client_class: MagicMock) -> None:
        """Test successful video deletion."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        analyzer = VideoAnalyzer(api_key="test-key")

        mock_file = MagicMock()
        mock_file.name = "test-file-name"

        analyzer._delete_video(mock_file)

        mock_client.files.delete.assert_called_once_with(name="test-file-name")

    @patch("src.analyzer.genai.Client")
    def test_delete_video_failure_logged(self, mock_client_class: MagicMock) -> None:
        """Test that deletion failure is logged but doesn't raise."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.files.delete.side_effect = Exception("Delete failed")

        analyzer = VideoAnalyzer(api_key="test-key")

        mock_file = MagicMock()
        mock_file.name = "test-file-name"

        # Should not raise
        analyzer._delete_video(mock_file)

    @patch("src.analyzer.genai.Client")
    def test_upload_video_waits_for_processing(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that upload waits for file to be processed."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # First return PROCESSING, then ACTIVE
        processing_file = MagicMock()
        processing_file.state.name = "PROCESSING"
        processing_file.name = "test-file"

        active_file = MagicMock()
        active_file.state.name = "ACTIVE"
        active_file.name = "test-file"

        mock_client.files.upload.return_value = processing_file
        mock_client.files.get.return_value = active_file

        analyzer = VideoAnalyzer(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            video_path = Path(f.name)

        try:
            with patch("src.analyzer.time.sleep"):
                result = analyzer._upload_video(video_path)

            assert result.state.name == "ACTIVE"
            mock_client.files.get.assert_called()
        finally:
            video_path.unlink()

    @patch("src.analyzer.genai.Client")
    def test_upload_video_fails_on_bad_state(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that upload raises on failed processing state."""
        from tenacity import RetryError

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        failed_file = MagicMock()
        failed_file.state.name = "FAILED"
        failed_file.name = "test-file"

        mock_client.files.upload.return_value = failed_file

        analyzer = VideoAnalyzer(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            video_path = Path(f.name)

        try:
            with (
                patch("src.analyzer.time.sleep"),
                pytest.raises((RuntimeError, RetryError)),
            ):
                # Will raise RetryError wrapping RuntimeError after retries
                analyzer._upload_video(video_path)
        finally:
            video_path.unlink()

    @patch("src.analyzer.genai.Client")
    def test_url_generation(self, mock_client_class: MagicMock) -> None:
        """Test that URL is correctly generated from shortcode."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"
        mock_file.name = "test-file"
        mock_client.files.upload.return_value = mock_file

        mock_response = MagicMock()
        mock_response.text = ExerciseAnalysis(
            muscle_group="legs",
            machine="squat rack",
            wrong_way="Knees caving",
            correct_way="Knees out",
            trainer_insights="Keep core tight",
        ).model_dump_json()
        mock_client.models.generate_content.return_value = mock_response

        analyzer = VideoAnalyzer(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            video_path = Path(f.name)

        try:
            with patch("src.analyzer.time.sleep"):
                result = analyzer.analyze(video_path, "SHORTCODE1")

            assert result.url == "https://www.instagram.com/p/SHORTCODE1/"
        finally:
            video_path.unlink()
