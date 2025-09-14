#!/bin/bash

# This script serves as a simple and safe runner for the safe_delete.py Python script.
# It validates the user's input before execution.

# --- Input Validation ---

# Check if exactly one argument was provided.
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 \"/path/to/directory\""
    echo "Error: You must provide the absolute path to the directory you want to process."
    exit 1
fi

TARGET_DIR="$1"

# Check if the provided path is a valid directory.
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: The path you provided is not a valid directory."
    echo "Path: '$TARGET_DIR'"
    exit 1
fi

# --- Execute Python Script ---

echo "Target Directory: \"$TARGET_DIR\""
echo "Starting the safe deletion process..."

# Execute the python script, passing the directory as a command-line argument.
# The path is quoted to handle spaces correctly.
python safe_delete.py --directory "$TARGET_DIR"

echo "Script execution finished."
