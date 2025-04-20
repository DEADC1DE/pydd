#!/bin/bash

# run_main.sh
# This script ensures that the Python virtual environment is activated or created,
# installs necessary dependencies, and runs the main.py script.
# It includes error handling for missing dependencies like Python3 and pip.

# Configuration
SCRIPT_DIR="/mnt/glftpd/bin/pydd"
VENV_DIR="$SCRIPT_DIR/venv"
ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
MAIN_SCRIPT="dd.py"

# Function to log messages with timestamps
log() {
    echo "($(date '+%Y-%m-%d')|$(date '+%H:%M:%S')) [$1]: $2"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Ensure the script directory exists
if [ ! -d "$SCRIPT_DIR" ]; then
    log "ERROR" "Script directory $SCRIPT_DIR does not exist."
    exit 1
fi

cd "$SCRIPT_DIR" || { log "ERROR" "Failed to change directory to $SCRIPT_DIR."; exit 1; }

# Check if Python3 is installed
if ! command_exists python3; then
    log "ERROR" "Python3 is not installed. Please install Python3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command_exists pip3; then
    log "ERROR" "pip3 is not installed. Please install pip3 and try again."
    exit 1
fi

# Activate or create virtual environment
if [ -f "$ACTIVATE_SCRIPT" ]; then
    log "INFO" "Activating existing virtual environment."
    source "$ACTIVATE_SCRIPT" || { log "ERROR" "Failed to activate virtual environment."; exit 1; }
else
    log "INFO" "Virtual environment not found. Creating one."
    
    # Create virtual environment
    python3 -m venv "$VENV_DIR" || { log "ERROR" "Failed to create virtual environment."; exit 1; }
    log "INFO" "Virtual environment created at $VENV_DIR."
    
    # Activate virtual environment
    source "$ACTIVATE_SCRIPT" || { log "ERROR" "Failed to activate virtual environment."; exit 1; }
    
    # Upgrade pip within the virtual environment
    pip install --upgrade pip || { log "ERROR" "Failed to upgrade pip in the virtual environment."; exit 1; }
    
    # Install dependencies
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE" || { log "ERROR" "Failed to install dependencies from $REQUIREMENTS_FILE."; exit 1; }
        log "INFO" "Dependencies installed successfully."
    else
        log "ERROR" "Requirements file $REQUIREMENTS_FILE not found."
        exit 1
    fi
fi

# Verify that the main.py script exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    log "ERROR" "Main script $MAIN_SCRIPT does not exist in $SCRIPT_DIR."
    exit 1
fi

# Run the main.py script with passed arguments
log "INFO" "Running $MAIN_SCRIPT with arguments: $*"
python3 "$MAIN_SCRIPT" "$@"
EXIT_CODE=$?

# Deactivate the virtual environment if it was activated by this script
if [ -f "$ACTIVATE_SCRIPT" ]; then
    deactivate
    log "INFO" "Virtual environment deactivated."
fi

# Exit with the same status as the Python script
exit $EXIT_CODE
