#!/bin/bash

# Contract FIPO Setup Script
# This script sets up the development environment for the contract-fipo project

set -e  # Exit on any error

echo "🚀 Setting up Contract FIPO development environment..."

# Check if Python 3.12+ is available
echo "📋 Checking Python version..."
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ $(echo "$PYTHON_VERSION >= 3.9" | bc -l) -eq 1 ]]; then
        PYTHON_CMD="python3"
    else
        echo "❌ Python 3.9+ is required. Current version: $PYTHON_VERSION"
        exit 1
    fi
else
    echo "❌ Python 3 not found. Please install Python 3.9+ first."
    exit 1
fi

echo "✅ Using Python: $($PYTHON_CMD --version)"

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install pdfplumber nltk spacy presidio-analyzer presidio-anonymizer openai sqlalchemy psycopg2-binary uvicorn fastapi tenacity celery redis python-multipart python-dotenv pydantic pydantic-settings

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install pytest pytest-asyncio pytest-mock black flake8 mypy

# Create .env file if it doesn't exist
echo "🔧 Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env file and add your xAI API key"
else
    echo "✅ .env file already exists"
fi

# Test installation
echo "🧪 Testing installation..."
python -c "import contract_fipo; print('✅ Package imported successfully')"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your xAI API key"
echo "2. Set up PostgreSQL database (see README.md for instructions)"
echo "3. Run: source venv/bin/activate"
echo "4. Test CLI: python -m contract_fipo.main --help"
echo "5. Start API: uvicorn contract_fipo.api:app --reload"
echo ""
echo "For detailed instructions, see README.md"