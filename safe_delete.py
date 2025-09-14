# ==================================================================================================
# safe_delete.py (v3 - Robust, Concurrent)
#
# This script deletes large directory structures safely.
# It is designed to be robust against the file system issues reported on Windows.
# This version uses a "discover-then-sort" method for guaranteed deletion order
# and a thread pool for concurrent deletion processing.
# ==================================================================================================

# --- Standard Library Imports ---
import os  # Used for basic path operations like os.path.join, os.listdir, etc.
import sys  # Used to access command-line arguments (sys.argv) and exit the script.
import argparse  # Used for parsing command-line arguments cleanly.
import logging  # Used for structured logging to file and console.
import subprocess  # Used to execute external shell commands (specifically 'rm').
import concurrent.futures  # Used for creating a thread pool for concurrent deletion.

# --- Configuration Constants ---

# The name for the log file that will contain the ordered list of paths to delete.
# This file acts as the "plan" for the deletion phase.
DELETION_LOG_FILENAME = "deletelog"

# The name for the file that will log errors and script progress.
ERROR_LOG_FILENAME = "error.log"

# The number of concurrent threads to use for the deletion process.
# As requested, this can be changed to scale the performance. For now, it's 1.
MAX_THREADS = 1

# --- Logger Setup ---

# Set up a global logger object.
# Using a global logger is a common practice in simpler applications.
logger = logging.getLogger(__name__)

def setup_logging(log_directory):
    """
    Configures the logging system to write all logs to a file.
    This ensures that all actions, errors, and progress are recorded for debugging.

    Args:
        log_directory (str): The directory where the error.log file will be created.
    """
    # Define the full path for the error log file.
    log_file_path = os.path.join(log_directory, ERROR_LOG_FILENAME)

    # Set the minimum level of logs to capture (INFO and above).
    logger.setLevel(logging.INFO)

    # Create a file handler to write log messages to the specified file.
    # Mode 'a' means append, so logs from multiple runs are kept.
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')

    # Define the format for the log messages to include timestamp, level, and message.
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Apply the formatter to the handler.
    file_handler.setFormatter(formatter)

    # Add the configured file handler to the logger.
    logger.addHandler(file_handler)

    # Also add a handler to stream logs to the console for real-time feedback.
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Log the successful initialization of the logging system.
    logger.info("Logging configured. Log file at: %s", log_file_path)

# --- Core Logic ---

def discover_paths_recursive(directory, all_paths):
    """
    A simple recursive function to discover all files and subdirectories.
    It does not perform any logic other than adding paths to a list.

    Args:
        directory (str): The current directory to scan.
        all_paths (list): The list to which all discovered paths are added.
    """
    # This function is designed to be simple. It first adds the directory itself.
    # This is important for the sorting step later.
    all_paths.append(directory)

    try:
        # Use os.listdir(), the most basic directory listing command.
        for item_name in os.listdir(directory):
            # Create the full path for the child item.
            full_path = os.path.join(directory, item_name)
            # Check if the item is a directory.
            if os.path.isdir(full_path):
                # If it's a directory, make a recursive call to dive deeper.
                discover_paths_recursive(full_path, all_paths)
            else:
                # If it's a file, just add its path to the list.
                all_paths.append(full_path)
    except OSError as e:
        # If we can't read a directory (e.g., permissions error), log it and continue.
        logger.error("Cannot access directory %s: %s", directory, e)

def delete_path_with_shell(path):
    """
    Deletes a single file or directory using the 'rm -rf' shell command.
    This function is designed to be called by the thread pool executor.

    Args:
        path (str): The absolute path to the item to delete.
    """
    # First, check if the path even exists. This makes the script resumable
    # and prevents errors if another thread deleted a parent directory already.
    # os.path.lexists is used to correctly handle broken symbolic links.
    if not os.path.lexists(path):
        logger.warning("Path not found (possibly already deleted), skipping: %s", path)
        return

    try:
        # Execute 'rm -rf' using subprocess.run.
        # This is the user-specified method for deletion.
        # '-r' handles directories, '-f' ignores errors for non-existent files
        # and suppresses confirmation prompts.
        # We pass the command as a list to prevent shell injection vulnerabilities.
        subprocess.run(["rm", "-rf", path], check=True, capture_output=True, text=True)
        # Log successful deletion.
        logger.info("Deleted: %s", path)
    except subprocess.CalledProcessError as e:
        # If the 'rm' command returns an error, log it.
        logger.error("Failed to delete %s. Error: %s", path, e.stderr.strip())
    except Exception as e:
        # Catch any other unexpected errors during the subprocess call.
        logger.error("An unexpected error occurred while trying to delete %s: %s", path, e)

# --- Main Execution Block ---

def main():
    """
    Main function to orchestrate the entire discovery and deletion process.
    """
    # Set up the argument parser to read the target directory from the command line.
    parser = argparse.ArgumentParser(
        description="Safely and concurrently delete large directory structures.",
        epilog="This script uses a 'discover-then-sort' method for safety and a thread pool for speed."
    )
    # The '--directory' argument is mandatory.
    parser.add_argument("--directory", type=str, required=True, help="The absolute path to the directory to process.")
    # Parse the arguments provided by the user.
    args = parser.parse_args()
    target_dir = args.directory

    # --- Pre-run validation ---
    # Check if the target directory exists and is actually a directory.
    if not os.path.isdir(target_dir):
        # Print directly to stderr and exit if the path is invalid.
        print(f"Error: The specified path is not a valid directory: {target_dir}", file=sys.stderr)
        sys.exit(1)

    # --- Phase 1: Discovery and Logging ---

    # Set up the logger to save logs inside the target directory.
    setup_logging(target_dir)

    logger.info("--- Starting Phase 1: Discovering all paths ---")
    # This list will hold all paths found by the recursive discovery.
    all_paths = []
    # Start the discovery process.
    discover_paths_recursive(target_dir, all_paths)
    logger.info("Discovered %d total files and directories.", len(all_paths))

    # --- The critical sorting step ---
    # Sort the list of paths in reverse alphabetical order.
    # This is a simple but powerful trick to ensure that child paths
    # (e.g., '/a/b/c.txt') always appear in the list *before* their parents ('/a/b/').
    # This guarantees a safe deletion order.
    logger.info("Sorting paths to ensure safe deletion order...")
    all_paths.sort(reverse=True)

    # Define the path for the deletion log file.
    deletion_log_path = os.path.join(target_dir, DELETION_LOG_FILENAME)

    try:
        # Write the sorted, safe-to-delete list to the log file.
        # This creates the execution plan for the next phase.
        with open(deletion_log_path, 'w', encoding='utf-8') as f:
            for path in all_paths:
                f.write(path + '\n')
        logger.info("Successfully created deletion plan at: %s", deletion_log_path)
    except IOError as e:
        # If the log file cannot be written, we cannot proceed.
        logger.critical("Failed to write deletion log file. Aborting. Error: %s", e)
        sys.exit(1)

    # --- Phase 2: Concurrent Deletion ---

    logger.info("--- Starting Phase 2: Deleting paths with %d threads ---", MAX_THREADS)

    # We use a ThreadPoolExecutor to manage a pool of worker threads.
    # This is the modern way to handle concurrency for I/O-bound tasks in Python.
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            # The 'executor.map' function applies the 'delete_path_with_shell' function
            # to each path in the 'all_paths' list. It automatically manages distributing
            # the work among the threads in the pool.
            # We pass the list directly, no need to read the file we just wrote, which is more efficient.
            executor.map(delete_path_with_shell, all_paths)

        # The 'with' block automatically waits for all threads to finish before exiting.
        logger.info("All deletion tasks completed.")

    except Exception as e:
        # Catch any high-level errors during the thread pool execution.
        logger.critical("A critical error occurred during the concurrent deletion phase: %s", e)
        sys.exit(1)

    # --- Final Step ---
    # After all contents are deleted, the log file itself, which is inside the target directory,
    # should also be gone, as its path would have been in the list.
    # The final `rm` call on the `target_dir` itself will remove the now-empty directory.
    logger.info("--- Safe deletion process finished successfully. ---")


# This standard Python entry point ensures that main() is called only when the script is executed directly.
if __name__ == "__main__":
    main()
