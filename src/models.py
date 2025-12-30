"""Pydantic models for structured video analysis output."""

from pydantic import BaseModel, Field


class ExerciseAnalysis(BaseModel):
    """Full analysis of a gym exercise video with correct/wrong technique comparison."""

    muscle_group: str = Field(
        description="Primary muscle group(s) targeted by this exercise (e.g., 'chest', 'back', 'legs', 'shoulders')"
    )
    machine: str = Field(
        description="Equipment or machine used for this exercise (e.g., 'cable machine', 'barbell', 'dumbbell', 'pec deck')"
    )
    wrong_way: str = Field(
        description="Detailed explanation of the incorrect technique shown in the video, including body positioning errors and why it's ineffective based on the myograph readings"
    )
    correct_way: str = Field(
        description="Detailed explanation of the correct technique shown in the video, including proper body positioning and why it's more effective based on the myograph readings"
    )
    trainer_insights: str = Field(
        description="Additional insights from the trainer including recommended sets, repetitions, tempo, common mistakes to avoid, and any general fitness tips mentioned"
    )


class GeneralInsights(BaseModel):
    """Fallback model for videos that don't match the exercise analysis structure."""

    trainer_insights: str = Field(
        description="Any useful fitness insights, tips, or information from the video"
    )
    video_type: str = Field(
        description="Brief description of what the video contains (e.g., 'motivational content', 'nutrition advice', 'Q&A session')"
    )


class VideoResult(BaseModel):
    """Result of analyzing a single video."""

    shortcode: str = Field(description="Instagram post shortcode")
    url: str = Field(description="Full Instagram URL")
    is_exercise_video: bool = Field(
        description="Whether this video matches the exercise analysis structure"
    )
    exercise_analysis: ExerciseAnalysis | None = Field(
        default=None, description="Full exercise analysis if applicable"
    )
    general_insights: GeneralInsights | None = Field(
        default=None, description="General insights for non-exercise videos"
    )
    error: str | None = Field(
        default=None, description="Error message if analysis failed"
    )


class ProgressState(BaseModel):
    """Tracks progress for resumable execution."""

    profile: str = Field(description="Instagram profile being analyzed")
    processed_shortcodes: list[str] = Field(
        default_factory=list, description="List of already processed post shortcodes"
    )
    results_file: str = Field(description="Path to the output results file")
