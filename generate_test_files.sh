#!/bin/bash

# This script generates a complex, randomized directory structure for testing the safe_delete.py script.

# --- Configuration ---
DEPTH=5
WIDTH=5
NUM_FILES=50

# --- Input Validation ---
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <test_directory_name>"
    exit 1
fi

ROOT_DIR=$1
echo "Generating test structure in directory: $ROOT_DIR"
# Clean up any previous test run
rm -rf "$ROOT_DIR"
mkdir -p "$ROOT_DIR"

# --- Directory Generation ---
# This function recursively creates the directory structure.
generate_dirs() {
    local current_dir=$1
    local current_depth=$2

    # Stop recursion when the desired depth is reached.
    if [ "$current_depth" -ge "$DEPTH" ]; then
        return
    fi

    # Create 'WIDTH' number of subdirectories in the current directory.
    for i in $(seq 1 $WIDTH); do
        local new_dir="$current_dir/subdir_${i}"
        mkdir -p "$new_dir"
        # Make a recursive call to create the next level.
        generate_dirs "$new_dir" $((current_depth + 1))
    done
}

echo "Creating directory structure ($DEPTH levels deep, $WIDTH wide)..."
generate_dirs "$ROOT_DIR" 0

# --- File Generation ---
echo "Finding all created subdirectories..."
# Create a list of all directories where files can be placed.
# 'find' is used to get a list of all directories under the root.
mapfile -t DIRS < <(find "$ROOT_DIR" -type d)
NUM_DIRS=${#DIRS[@]}
echo "Found $NUM_DIRS directories to populate."

echo "Generating $NUM_FILES random files..."
# Loop to create the specified number of files.
for i in $(seq 1 $NUM_FILES); do
    # Pick a random directory from the list.
    # $RANDOM is a bash variable that gives a random integer.
    RANDOM_DIR_IDX=$((RANDOM % NUM_DIRS))
    TARGET_DIR=${DIRS[$RANDOM_DIR_IDX]}

    # Create a uniquely named file in the chosen directory.
    # Using 'touch' is a simple way to create an empty file.
    touch "$TARGET_DIR/random_file_$i.txt"
done

echo "Test file generation complete."
# Use 'find' again to give a summary of what was created.
echo "--- Summary ---"
echo "Total directories: $(find "$ROOT_DIR" -type d | wc -l)"
echo "Total files: $(find "$ROOT_DIR" -type f | wc -l)"
echo "----------------"
