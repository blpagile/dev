#!/bin/bash

# install.sh - Installation script for Contract FIPO
# This script automates the setup process based on the README.md file.

set -e # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting installation for Contract FIPO..."

# --- 1. Check for Python ---
echo "🔎 Checking for Python 3.12+..."
PYTHON_CMD=""
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    # Check if python3 is version 3.12 or higher
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ "$(printf '%s\n' "3.12" "$PY_VERSION" | sort -V | head -n1)" == "3.12" ]]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Error: Python 3.12 or higher is required."
    echo "Please install a compatible Python version and try again."
    exit 1
fi
echo "✅ Found compatible Python: $($PYTHON_CMD --version)"

# --- 2. Check for and Install Poetry ---
echo "🔎 Checking for Poetry..."
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
    # Add poetry to PATH for the current session
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ Poetry installed."
else
    echo "✅ Poetry is already installed."
fi

# --- 3. Configure Poetry and Install Dependencies ---
echo "⚙️ Configuring Poetry to create a virtual environment in the project..."
poetry config virtualenvs.in-project true

echo "📦 Installing Python dependencies with Poetry..."
poetry install

echo "✅ Python dependencies installed successfully."

# --- 4. Setup Environment Configuration ---
echo "📝 Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "✅ Created .env file from .env.template."
        echo "⚠️ IMPORTANT: Please edit the .env file to add your XAI_API_KEY and database credentials."
    else
        echo "⚠️ Warning: .env.template not found. Please create a .env file manually."
    fi
else
    echo "✅ .env file already exists. Skipping creation."
fi

# --- 5. Download spaCy Language Model ---
echo "🧠 Downloading spaCy language model for enhanced NLP..."
poetry run python -m spacy download en_core_web_sm
echo "✅ spaCy model downloaded."

# --- 6. Check for System Dependencies (PostgreSQL & Redis) ---
echo "🔎 Checking for system dependencies (PostgreSQL & Redis)..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS. Checking for Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "⚠️ Homebrew not found. Please install Homebrew to automatically install PostgreSQL and Redis."
        echo "See https://brew.sh/"
    else
        echo "✅ Homebrew found."
        # Install PostgreSQL
        if ! command -v psql &> /dev/null; then
            echo "PostgreSQL not found. Installing with Homebrew..."
            brew install postgresql@14
            brew services start postgresql@14
            echo "✅ PostgreSQL installed and started."
        else
            echo "✅ PostgreSQL is already installed."
        fi
        # Install Redis
        if ! command -v redis-cli &> /dev/null; then
            echo "Redis not found. Installing with Homebrew..."
            brew install redis
            brew services start redis
            echo "✅ Redis installed and started."
        else
            echo "✅ Redis is already installed."
        fi
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux. Please ensure PostgreSQL and Redis are installed."
    echo "On Debian/Ubuntu, you can use: sudo apt-get install postgresql redis-server"
    echo "On Fedora/CentOS, you can use: sudo dnf install postgresql-server redis"
else
    echo "⚠️ Unsupported OS for automatic dependency installation. Please install PostgreSQL and Redis manually."
fi

# --- 7. Final Instructions ---
echo ""
echo "🎉 Installation complete! 🎉"
echo ""
echo "Next Steps:"
echo "1. (IMPORTANT) Edit the .env file with your API keys and database URL."
echo "2. Set up your PostgreSQL database and user as described in the README.md."
echo "3. Activate the virtual environment by running: poetry shell"
echo "4. Once inside the shell, you can run the application:"
echo "   - Test the database connection: python -m contract_fipo.main --test-db"
echo "   - Start the API server: uvicorn contract_fipo.api:app --reload"
echo ""
echo "For more details, please refer to the README.md file."
