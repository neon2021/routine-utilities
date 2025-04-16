#!/bin/bash

# Get the script directory
DIR="$(dirname "$(readlink -f "$0")")"
SCRIPT_PATH="$DIR/run_transcriber.sh"
NAUTILUS_EXT_PATH="$DIR/transcriber_extension.py"

echo "Installing Audio/Video Transcriber..."

# Make scripts executable
chmod +x "$SCRIPT_PATH"

# Install desktop file for application launchers
mkdir -p "$HOME/.local/share/applications"
cp "$DIR/transcriber.desktop" "$HOME/.local/share/applications/"
sed -i "s|Exec=bash -c 'cd \$HOME/Documents/code-projects/routine-utilities && ./run_transcriber.sh|Exec=bash -c '$SCRIPT_PATH|g" "$HOME/.local/share/applications/transcriber.desktop"

# Install Thunar custom action
if command -v thunar &> /dev/null; then
    echo "Installing Thunar custom action..."
    mkdir -p "$HOME/.config/Thunar/uca.xml.d"
    cp "$DIR/transcriber-thunar-action.desktop" "$HOME/.config/Thunar/uca.xml.d/"
    sed -i "s|Exec=/home/caesar/Documents/code-projects/routine-utilities/run_transcriber.sh|Exec=$SCRIPT_PATH|g" "$HOME/.config/Thunar/uca.xml.d/transcriber-thunar-action.desktop"
    
    # If uca.xml exists, update it
    if [ -f "$HOME/.config/Thunar/uca.xml" ]; then
        echo "Updating Thunar custom actions configuration..."
        thunar --quit
        sleep 1
    fi
else
    echo "Thunar not found. Skipping Thunar integration."
fi

# Install Nautilus extension
if command -v nautilus &> /dev/null; then
    echo "Installing Nautilus extension..."
    # Check if python3-nautilus is installed
    if ! dpkg -l | grep -q python3-nautilus; then
        echo "python3-nautilus is not installed. To install Nautilus extension, run:"
        echo "sudo apt install python3-nautilus"
        echo "Then run this script again."
    else
        mkdir -p "$HOME/.local/share/nautilus-python/extensions"
        cp "$NAUTILUS_EXT_PATH" "$HOME/.local/share/nautilus-python/extensions/"
        # Update the path in the extension
        sed -i "s|script_path = os.path.expanduser('~/Documents/code-projects/routine-utilities/run_transcriber.sh')|script_path = '$SCRIPT_PATH'|g" "$HOME/.local/share/nautilus-python/extensions/transcriber_extension.py"
        
        # Restart Nautilus
        nautilus -q
        echo "Nautilus extension installed. Nautilus has been restarted."
    fi
else
    echo "Nautilus not found. Skipping Nautilus integration."
fi

echo "Installation complete!"
echo "You can now use the Audio/Video Transcriber by right-clicking on audio or video files." 