# AI Training Video Analyzer

Analyzes gym training videos from Instagram profiles using Google's Gemini AI. Extracts structured information about exercises, techniques, and trainer insights.

## Features

- Downloads videos from Instagram profiles
- Analyzes videos using Gemini 3 Flash with structured output
- Extracts: muscle groups, equipment, wrong/correct techniques, trainer insights
- Handles EMG/myograph chart analysis for technique comparison
- Rate limiting and retry logic for reliable operation
- Resumable execution (continues from where it stopped)
- No database required - uses simple JSON files for progress tracking

## Prerequisites

1. **Python 3.11+**
2. **Google AI API Key**: Get one at https://aistudio.google.com/apikey
3. **Instagram credentials** (username/password)

## Installation

```bash
cd ai-training

# Install with uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env and add your credentials
```

## Usage

### Step 1: Collect Post Shortcodes from Instagram

Instagram uses virtual scrolling, so you need to collect post IDs using a browser script.

1. Open the Instagram profile in your browser
2. Open DevTools Console (F12 → Console)
3. Paste the script from `scripts/collect_instagram_posts.js`
4. Wait for it to finish scrolling and collecting
5. Save the JSON array to `data/<profile>.json`

### Step 2: Fetch Video URLs

```bash
uv run python -m src.cli parse-shortcodes data/<profile>.json -p <profile>
```

This fetches video URLs for each shortcode and saves to `data/videos_<profile>.json`.

Options:
- `-p, --profile NAME` - Profile name for the output file
- `-o, --output FILE` - Output JSON file path
- `--fresh` - Start fresh, ignore existing progress
- `-v, --verbose` - Enable debug logging

### Step 3: Analyze Videos

```bash
uv run python -m src.cli analyze data/videos_<profile>.json -m 10
```

Options:
- `-o, --output DIR` - Output directory (default: ./output)
- `-m, --max-videos N` - Limit number of videos to process
- `-v, --verbose` - Enable debug logging

### Alternative: List Videos via API (may hit rate limits)

```bash
uv run python -m src.cli list-videos <profile>
```

This uses Instagram's API directly but may be rate-limited for large profiles.

## Example Workflow

```bash
# 1. Collect shortcodes (in browser, see scripts/collect_instagram_posts.js)
# Save output to data/alexeysmirnov__.json

# 2. Fetch video URLs (resumable)
uv run python -m src.cli -v parse-shortcodes data/alexeysmirnov__.json -p alexeysmirnov__

# 3. Analyze videos (resumable)
uv run python -m src.cli -v analyze data/videos_alexeysmirnov__.json -m 20
```

## Output Format

Results are saved as JSONL (JSON Lines) in the output directory:

```
output/
├── results_profilename.jsonl    # Analysis results
└── .progress_profilename.json   # Progress tracking (for resume)
```

### Result Structure

Each line in the JSONL file contains:

```json
{
  "shortcode": "ABC123",
  "url": "https://www.instagram.com/p/ABC123/",
  "is_exercise_video": true,
  "exercise_analysis": {
    "muscle_group": "pectoralis major",
    "machine": "pec deck machine",
    "wrong_way": "Shoulders rolled forward, reducing chest activation...",
    "correct_way": "Chest up, shoulders back, focusing on squeeze...",
    "trainer_insights": "3-4 sets of 12-15 reps, 2 second squeeze at peak..."
  },
  "general_insights": null,
  "error": null
}
```

For non-exercise videos:

```json
{
  "shortcode": "XYZ789",
  "url": "https://www.instagram.com/p/XYZ789/",
  "is_exercise_video": false,
  "exercise_analysis": null,
  "general_insights": {
    "trainer_insights": "Rest days are important for muscle recovery...",
    "video_type": "motivational content"
  },
  "error": null
}
```

## Resuming Interrupted Runs

All commands are resumable. Simply run the same command again - it will skip already-processed items and continue from where it stopped.

## Customizing the Analysis Prompt

The analysis prompt is located at `src/prompts/analysis.txt`. You can modify it to:
- Add specific questions for your use case
- Change the focus of the analysis
- Add language-specific instructions

## Rate Limiting

The script includes built-in rate limiting:
- Instagram: 2-5 second delay between requests with jitter
- Gemini API: 1 second delay between requests
- Automatic exponential backoff on rate limit errors
- Up to 3 retries for failed requests

## Development

```bash
# Run tests
pytest

# Lint and format
ruff check . --fix
ruff format .

# Type check
mypy src
```

## Troubleshooting

### Rate limit errors (403/429)
The script handles these automatically with exponential backoff. If persistent:
- Wait 15-30 minutes before retrying
- The `parse-shortcodes` command is resumable - just run it again

### "login_required" warnings
These are for high-quality video versions and can be ignored. Standard quality videos are still fetched.

### Video analysis fails
Some videos may not match the expected structure. These are logged and saved with `general_insights` instead of `exercise_analysis`.
