# ==================================================================================================
# safe_delete.py (v2 - Manual Recursion)
#
# A script for safely deleting large directory structures using a manual recursive function
# to build the deletion log, as per user's specific instructions.
# ==================================================================================================

# --- Import necessary libraries ---
import os  # For basic file system operations like listdir, path.join, path.isdir.
import sys  # To access command-line arguments and exit.
import argparse  # For parsing command-line arguments.
import logging  # For logging errors and progress.
import subprocess  # To run the external 'rm' shell command.

# --- Global Constants ---
# The name of the file that will log the list of items to delete.
DELETION_LOG_FILENAME = "deletelog"
# The name of the file for logging errors and warnings.
ERROR_LOG_FILENAME = "error.log"

# --- Logger Setup ---
# Setup a global logger variable.
logger = logging.getLogger(__name__)

def setup_logging(log_directory):
    """
    Configures the logging system to write logs to a file.
    Args:
        log_directory (str): The directory where the error log file will be created.
    """
    # Create the full path for the error log file.
    log_file_path = os.path.join(log_directory, ERROR_LOG_FILENAME)
    # Set the logging level to INFO.
    logger.setLevel(logging.INFO)
    # Create a file handler to write logs to a file. 'a' for append mode.
    handler = logging.FileHandler(log_file_path, mode='a')
    # Ensure logs are written immediately.
    handler.flush = sys.stdout.flush
    # Define the log message format.
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # Add the file handler and a console handler to the logger.
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.info("Logging configured. Errors will be saved to %s", log_file_path)

# --- Core Logic: Manual Recursion for Logging ---

def create_deletion_log_recursive(directory, log_file_handle):
    """
    Manually implements a recursive, post-order traversal to create a deletion log.
    This avoids using os.walk, per user instructions.

    The order of operations is:
    1. Log all files in the current directory.
    2. Recurse into all subdirectories.
    3. Log the current directory itself (after all its contents have been logged).

    Args:
        directory (str): The path to the directory to process.
        log_file_handle: An open file handle to write the log to.
    """
    # These lists will hold the immediate children of the current directory.
    files = []
    subdirectories = []
    try:
        # os.listdir is the approved primitive for getting directory contents.
        for item_name in os.listdir(directory):
            # Construct the full, absolute path for the item.
            full_path = os.path.join(directory, item_name)
            # Check if the item is a directory or a file/link.
            if os.path.isdir(full_path):
                subdirectories.append(full_path)
            else:
                files.append(full_path)
    except OSError as e:
        logger.error("Could not read directory %s: %s", directory, e)
        return # Stop processing this directory if it can't be read.

    # 1. First, write all files in the current directory to the log.
    for file_path in files:
        log_file_handle.write(file_path + '\n')

    # 2. Second, recurse into the subdirectories.
    # This is the 'depth-first' part of the search.
    for subdir_path in subdirectories:
        create_deletion_log_recursive(subdir_path, log_file_handle)

    # 3. Finally, after all files and subdirectories have been logged,
    # log the directory itself. This is the 'post-order' part.
    log_file_handle.write(directory + '\n')

# --- Deletion Logic ---

def delete_with_shell(path):
    """
    Deletes a file or directory using the external 'rm' shell command.
    This is the only deletion method, per user instructions.
    Args:
        path (str): The absolute path to the file or directory to delete.
    """
    try:
        # Use subprocess.run to execute 'rm -rf'. This is robust.
        subprocess.run(["rm", "-rf", path], check=True, capture_output=True, text=True)
        logger.info("Successfully deleted (Shell): %s", path)
    except subprocess.CalledProcessError as e:
        # Log any error from the shell command.
        logger.error("Failed to delete (Shell) %s: %s", path, e.stderr)

def process_deletion_list(log_file_path):
    """
    Reads the deletion log file and deletes each item using the shell command.
    Args:
        log_file_path (str): The path to the file containing the list of items to delete.
    """
    logger.info("Phase 2: Starting to process the deletion list...")
    if not os.path.exists(log_file_path):
        logger.error("Deletion log file not found at %s. Cannot proceed.", log_file_path)
        return

    # Open the log file for reading.
    with open(log_file_path, 'r', encoding='utf-8') as f:
        # Read all paths into memory.
        paths_to_delete = f.readlines()

    # Iterate through the paths and delete them.
    for path in paths_to_delete:
        path = path.strip() # Remove trailing newline.
        if path:
            # Check if the item still exists to make the script resumable.
            if os.path.exists(path) or os.path.islink(path):
                delete_with_shell(path)
            else:
                logger.info("Item already deleted, skipping: %s", path)

    logger.info("Phase 2: Finished processing deletion list.")

# --- Main Execution Block ---

def main():
    """
    The main function that orchestrates the script's execution.
    """
    parser = argparse.ArgumentParser(description="Safely delete large directory structures using manual recursion.")
    parser.add_argument("--directory", type=str, required=True, help="The absolute path to the directory to process.")
    args = parser.parse_args()
    target_dir = args.directory

    # --- Pre-run checks ---
    if not os.path.isdir(target_dir):
        print(f"Error: The specified directory does not exist: {target_dir}")
        sys.exit(1)

    # --- Setup ---
    setup_logging(target_dir)
    deletion_log_path = os.path.join(target_dir, DELETION_LOG_FILENAME)

    try:
        # --- Phase 1: Build the deletion list using manual recursion ---
        logger.info("Phase 1: Starting to build the deletion list with manual recursion...")
        with open(deletion_log_path, 'w', encoding='utf-8') as log_file:
            create_deletion_log_recursive(target_dir, log_file)
        logger.info("Phase 1: Successfully created deletion list at %s", deletion_log_path)

        # --- Phase 2: Process the list and delete items ---
        process_deletion_list(deletion_log_path)

        logger.info("Safe deletion process completed successfully.")

    except Exception as e:
        logger.critical("An unexpected error occurred: %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
