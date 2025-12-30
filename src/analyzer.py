"""Gemini video analyzer with structured output."""

import logging
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.models import ExerciseAnalysis, GeneralInsights, VideoResult

logger = logging.getLogger(__name__)

# Gemini model to use
MODEL_NAME = "gemini-3-flash-preview"

# Rate limiting for Gemini API
GEMINI_REQUEST_DELAY_SECONDS = 1.0


def _load_prompt() -> str:
    """Load the analysis prompt from file."""
    prompt_path = Path(__file__).parent / "prompts" / "analysis.txt"
    return prompt_path.read_text()


class VideoAnalyzer:
    """Analyzes gym training videos using Gemini AI."""

    def __init__(self, api_key: str) -> None:
        """Initialize the analyzer.

        Args:
            api_key: Google AI API key.
        """
        # Clear conflicting env var so SDK uses the provided key
        os.environ.pop("GOOGLE_API_KEY", None)
        self._client = genai.Client(api_key=api_key)
        self._prompt = _load_prompt()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=10, max=120),
        before_sleep=lambda retry_state: logger.warning(
            f"Gemini API error, retrying in {retry_state.next_action.sleep}s..."
        ),
    )
    def _upload_video(self, video_path: Path) -> types.File:
        """Upload video to Gemini and wait for processing."""
        logger.info(f"Uploading video to Gemini: {video_path}")
        video_file = self._client.files.upload(file=str(video_path))

        # Wait for file to be processed
        while video_file.state.name == "PROCESSING":
            logger.debug(f"Waiting for file {video_file.name} to be processed...")
            time.sleep(5)
            video_file = self._client.files.get(name=video_file.name)

        if video_file.state.name != "ACTIVE":
            raise RuntimeError(f"File processing failed: {video_file.state.name}")

        logger.info(f"Video uploaded and ready: {video_file.name}")
        return video_file

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=10, max=120),
    )
    def _analyze_with_schema(self, video_file: types.File, schema: type) -> str:
        """Run analysis with a specific schema."""
        time.sleep(GEMINI_REQUEST_DELAY_SECONDS)

        response = self._client.models.generate_content(
            model=MODEL_NAME,
            contents=[video_file, self._prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        return response.text

    def _delete_video(self, video_file: types.File) -> None:
        """Delete uploaded video from Gemini."""
        try:
            self._client.files.delete(name=video_file.name)
            logger.debug(f"Deleted video from Gemini: {video_file.name}")
        except Exception as e:
            logger.warning(f"Failed to delete video from Gemini: {e}")

    def analyze(self, video_path: Path, shortcode: str) -> VideoResult:
        """Analyze a video and return structured results.

        Args:
            video_path: Path to the video file.
            shortcode: Instagram post shortcode.

        Returns:
            VideoResult with analysis or error.
        """
        url = f"https://www.instagram.com/p/{shortcode}/"
        video_file = None

        try:
            # Upload video
            video_file = self._upload_video(video_path)

            # Try full exercise analysis first
            try:
                logger.info(f"Analyzing video with full schema: {shortcode}")
                response_text = self._analyze_with_schema(video_file, ExerciseAnalysis)
                exercise_analysis = ExerciseAnalysis.model_validate_json(response_text)

                return VideoResult(
                    shortcode=shortcode,
                    url=url,
                    is_exercise_video=True,
                    exercise_analysis=exercise_analysis,
                )

            except (ValidationError, Exception) as e:
                logger.info(
                    f"Video {shortcode} doesn't match exercise schema, "
                    f"trying general insights: {e}"
                )

                # Fall back to general insights
                response_text = self._analyze_with_schema(video_file, GeneralInsights)
                general_insights = GeneralInsights.model_validate_json(response_text)

                return VideoResult(
                    shortcode=shortcode,
                    url=url,
                    is_exercise_video=False,
                    general_insights=general_insights,
                )

        except Exception as e:
            logger.error(f"Failed to analyze video {shortcode}: {e}")
            return VideoResult(
                shortcode=shortcode,
                url=url,
                is_exercise_video=False,
                error=str(e),
            )

        finally:
            # Clean up uploaded video
            if video_file:
                self._delete_video(video_file)
