#!/bin/bash

# Get the directory of this script
DIR="$(dirname "$(readlink -f "$0")")"

# Export GUI_MODE=1 to indicate we're running from Thunar
export GUI_MODE=1

# Run the transcriber with the provided file(s)
python3 "$DIR/transcriber.py" "$@" 