"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.models import (
    ExerciseAnalysis,
    GeneralInsights,
    ProgressState,
    VideoResult,
)


class TestExerciseAnalysis:
    """Tests for ExerciseAnalysis model."""

    def test_valid_exercise_analysis(self) -> None:
        """Test creating a valid exercise analysis."""
        analysis = ExerciseAnalysis(
            muscle_group="chest",
            machine="cable machine",
            wrong_way="Rounded back, elbows flared",
            correct_way="Straight back, elbows tucked",
            trainer_insights="3 sets of 12 reps",
        )
        assert analysis.muscle_group == "chest"
        assert analysis.machine == "cable machine"
        assert "Rounded back" in analysis.wrong_way
        assert "Straight back" in analysis.correct_way
        assert "3 sets" in analysis.trainer_insights

    def test_exercise_analysis_json_roundtrip(self) -> None:
        """Test JSON serialization and deserialization."""
        analysis = ExerciseAnalysis(
            muscle_group="back",
            machine="lat pulldown",
            wrong_way="Using momentum",
            correct_way="Slow controlled movement",
            trainer_insights="Focus on mind-muscle connection",
        )
        json_str = analysis.model_dump_json()
        restored = ExerciseAnalysis.model_validate_json(json_str)
        assert restored == analysis

    def test_exercise_analysis_missing_field(self) -> None:
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            ExerciseAnalysis(
                muscle_group="chest",
                machine="bench press",
                # missing wrong_way, correct_way, trainer_insights
            )


class TestGeneralInsights:
    """Tests for GeneralInsights model."""

    def test_valid_general_insights(self) -> None:
        """Test creating valid general insights."""
        insights = GeneralInsights(
            trainer_insights="Stay hydrated during workouts",
            video_type="motivational content",
        )
        assert "hydrated" in insights.trainer_insights
        assert insights.video_type == "motivational content"

    def test_general_insights_json_roundtrip(self) -> None:
        """Test JSON serialization and deserialization."""
        insights = GeneralInsights(
            trainer_insights="Nutrition is key",
            video_type="nutrition advice",
        )
        json_str = insights.model_dump_json()
        restored = GeneralInsights.model_validate_json(json_str)
        assert restored == insights


class TestVideoResult:
    """Tests for VideoResult model."""

    def test_exercise_video_result(self) -> None:
        """Test VideoResult for an exercise video."""
        analysis = ExerciseAnalysis(
            muscle_group="legs",
            machine="leg press",
            wrong_way="Knees caving in",
            correct_way="Knees tracking over toes",
            trainer_insights="Don't lock out at the top",
        )
        result = VideoResult(
            shortcode="ABC123",
            url="https://www.instagram.com/p/ABC123/",
            is_exercise_video=True,
            exercise_analysis=analysis,
        )
        assert result.shortcode == "ABC123"
        assert result.is_exercise_video is True
        assert result.exercise_analysis is not None
        assert result.general_insights is None
        assert result.error is None

    def test_non_exercise_video_result(self) -> None:
        """Test VideoResult for a non-exercise video."""
        insights = GeneralInsights(
            trainer_insights="Q&A session about supplements",
            video_type="Q&A session",
        )
        result = VideoResult(
            shortcode="XYZ789",
            url="https://www.instagram.com/p/XYZ789/",
            is_exercise_video=False,
            general_insights=insights,
        )
        assert result.shortcode == "XYZ789"
        assert result.is_exercise_video is False
        assert result.exercise_analysis is None
        assert result.general_insights is not None

    def test_error_video_result(self) -> None:
        """Test VideoResult with an error."""
        result = VideoResult(
            shortcode="ERR001",
            url="https://www.instagram.com/p/ERR001/",
            is_exercise_video=False,
            error="Failed to download video",
        )
        assert result.error == "Failed to download video"
        assert result.exercise_analysis is None
        assert result.general_insights is None

    def test_video_result_json_roundtrip(self) -> None:
        """Test JSON serialization and deserialization."""
        analysis = ExerciseAnalysis(
            muscle_group="shoulders",
            machine="dumbbell",
            wrong_way="Swinging weights",
            correct_way="Controlled movement",
            trainer_insights="Keep core tight",
        )
        result = VideoResult(
            shortcode="TEST01",
            url="https://www.instagram.com/p/TEST01/",
            is_exercise_video=True,
            exercise_analysis=analysis,
        )
        json_str = result.model_dump_json()
        restored = VideoResult.model_validate_json(json_str)
        assert restored == result


class TestProgressState:
    """Tests for ProgressState model."""

    def test_empty_progress_state(self) -> None:
        """Test creating an empty progress state."""
        state = ProgressState(
            profile="test_user",
            results_file="/path/to/results.jsonl",
        )
        assert state.profile == "test_user"
        assert state.processed_shortcodes == []
        assert state.results_file == "/path/to/results.jsonl"

    def test_progress_state_with_processed(self) -> None:
        """Test progress state with processed shortcodes."""
        state = ProgressState(
            profile="test_user",
            processed_shortcodes=["ABC123", "XYZ789"],
            results_file="/path/to/results.jsonl",
        )
        assert len(state.processed_shortcodes) == 2
        assert "ABC123" in state.processed_shortcodes

    def test_progress_state_json_roundtrip(self) -> None:
        """Test JSON serialization and deserialization."""
        state = ProgressState(
            profile="gym_trainer",
            processed_shortcodes=["A", "B", "C"],
            results_file="results.jsonl",
        )
        json_str = state.model_dump_json()
        restored = ProgressState.model_validate_json(json_str)
        assert restored == state
