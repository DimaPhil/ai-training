#!/bin/bash
# Analyze videos from a collected video list
#
# Usage: ./scripts/analyze_videos.sh [video_list.json] [max_videos]
#
# Example:
#   ./scripts/analyze_videos.sh data/videos_alexeysmirnov__.json 10

set -e

VIDEO_LIST="${1:-data/videos_alexeysmirnov__.json}"
MAX_VIDEOS="${2:-}"

if [ ! -f "$VIDEO_LIST" ]; then
    echo "Error: Video list not found: $VIDEO_LIST"
    exit 1
fi

# Count videos in list
VIDEO_COUNT=$(python3 -c "import json; print(len(json.load(open('$VIDEO_LIST'))['videos']))")
echo "Found $VIDEO_COUNT videos in $VIDEO_LIST"

# Build command
CMD="uv run python -m src.cli -v analyze $VIDEO_LIST"
if [ -n "$MAX_VIDEOS" ]; then
    CMD="$CMD -m $MAX_VIDEOS"
    echo "Processing max $MAX_VIDEOS videos"
fi

echo "Running: $CMD"
echo "Results will be saved to: output/"
echo ""

$CMD
