#!/bin/bash

# Script to ensure commands are run with the correct virtual environment

# Check if Poetry is installed
if command -v poetry &> /dev/null; then
    echo "Using Poetry to run command..."
    poetry run "$@"
else
    echo "Poetry not found. Attempting to activate virtual environment manually..."
    # Assuming virtual environment is in .venv in project root or managed by Poetry
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        echo "Virtual environment activated from .venv"
        "$@"
    else
        echo "Error: No virtual environment found. Please ensure Poetry or a virtual environment is set up."
        exit 1
    fi
fi
