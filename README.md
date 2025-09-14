# Safe Deletion Tool (v2 - Manual Recursion)

This tool is designed to safely and recursively delete large directory structures, particularly on systems like Windows 10 where standard deletion methods can fail or hang.

This version has been re-engineered to use a manual, low-level recursive function to discover files, avoiding higher-level Python functions like `os.walk` to ensure maximum compatibility and adherence to the core design principles.

## How it Works

The tool operates in two distinct phases to ensure stability and recoverability:

1.  **Analysis Phase**: It performs a Depth-First Search (DFS) through the target directory using a custom-built recursive function. This function uses only basic `os.listdir` calls to discover contents. It creates a log file (`deletelog`) containing the absolute paths of every file and directory, listed from the deepest part of the structure upwards (a post-order traversal).

2.  **Deletion Phase**: It reads the `deletelog` file and deletes each item individually using only the `rm` shell command, executed via a subprocess. This one-by-one, external-process approach is designed to be slow but steady, avoiding the issues that can plague native file system APIs on problematic systems.

## Usage

The tool is run via the `run.sh` bash script. Simply provide the absolute path to the directory you wish to clear.

```bash
./run.sh "/path/to/your/directory"
```

The script will then begin the two-phase process of logging and deleting.

### IMPORTANT NOTES:
- This script is designed to be run in a Bash-like environment on Windows (e.g., Git Bash, WSL) where the `rm` command is available.
- The target directory path MUST be an **absolute path**.
- The script will leave the top-level target directory in place, containing the `deletelog` and `error.log` files for post-run analysis. All contents within it will be deleted.
