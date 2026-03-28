#!/bin/bash

# Convert Animated GIF to WebM using VP9
# Automatically suggested from acceptance criteria

if [ "$#" -eq 0 ]; then
    echo "Usage: ./convert_gif.sh <input.gif> [output.webm]"
    exit 1
fi

INPUT="$1"
if [ ! -f "$INPUT" ]; then
    echo "Error: File '$INPUT' not found."
    exit 1
fi

# if second param is not provided, use the first param's basename with .webm extension
OUTPUT="${2:-${INPUT%.*}.webm}"

echo "Converting $INPUT to $OUTPUT using VP9 codec..."
ffmpeg -i "$INPUT" -c:v libvpx-vp9 -b:v 0 -crf 41 "$OUTPUT" -y

echo "====================================="
echo "Conversion complete: $OUTPUT"
ORIG_SIZE=$(stat -c%s "$INPUT" 2>/dev/null || stat -f%z "$INPUT")
NEW_SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT")
RATIO=$(awk "BEGIN {printf \"%.2f\", ($NEW_SIZE/$ORIG_SIZE)*100}")
echo "Original size: $(($ORIG_SIZE/1024)) KB"
echo "New size: $(($NEW_SIZE/1024)) KB ($RATIO% of original)"
