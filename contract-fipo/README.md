# Contract FIPO

A comprehensive contract analysis tool with PII detection and Grok AI integration. This tool parses PDF and text contracts, detects and tokenizes personally identifiable information (PII), analyzes contracts using xAI's Grok API, and stores results in a PostgreSQL database.

## Features

- 📄 **Document Parsing**: Support for PDF and text files with robust text extraction
- 🔒 **PII Protection**: Automatic detection and tokenization of sensitive information
- 🤖 **AI Analysis**: Contract analysis using xAI's Grok API with structured JSON output
- 🗄️ **Database Storage**: PostgreSQL integration for storing analysis results
- 🌐 **Web API**: FastAPI-based REST API for scalable processing
- 🔄 **Retry Logic**: Robust error handling with exponential backoff
- ⚡ **Async Processing**: Background task processing with Celery and Redis
- 🧪 **Comprehensive Testing**: Full test suite with pytest

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [Web API](#web-api)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Prerequisites

- Python 3.12 or higher
- PostgreSQL 14 or higher
- Redis (for background task processing)
- xAI API key

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd contract-fipo
```

### 2. Install Poetry (if not already installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. Install Dependencies

```bash
# Install project dependencies
poetry install

# Activate the virtual environment (created in the project directory)
source .venv/bin/activate
```

### 4. Using run_with_env.sh for Commands

To ensure that all commands are run within the correct virtual environment, use the provided `run_with_env.sh` script. This script will attempt to use Poetry if installed, or activate the local virtual environment.

```bash
# Example of running a command with the virtual environment
./run_with_env.sh pytest

# Running the application
./run_with_env.sh python -m contract_fipo.main --file path/to/contract.pdf

# Running the API server
./run_with_env.sh uvicorn contract_fipo.api:app --reload --host 0.0.0.0 --port 8000
```

### 4. Install System Dependencies (macOS)

```bash
# Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# Install Redis
brew install redis
brew services start redis
```

### 5. Download spaCy Language Model (Optional)

If using spaCy for enhanced NLP processing:

```bash
poetry run python -m spacy download en_core_web_sm
```

## Database Setup

### 1. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE contracts_db;
CREATE USER contract_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE contracts_db TO contract_user;
\q
```

### 2. Update Database Configuration

Edit your `.env` file with the database credentials:

```bash
DATABASE_URL=postgresql://contract_user:your_password@localhost/contracts_db
```

### 3. Initialize Database Tables

The application will automatically create the required tables on first run, or you can test the connection:

```bash
poetry run python -m contract_fipo.main --test-db
```

## Configuration

### 1. Environment Variables

Copy the template and configure your environment:

```bash
cp .env.template .env
```

Edit `.env` with your configuration:

```env
# xAI API Configuration
XAI_API_KEY=your_xai_api_key_here

# Database Configuration
DATABASE_URL=postgresql://contract_user:your_password@localhost/contracts_db

# Redis Configuration (for Celery)
REDIS_URL=redis://localhost:6379/0

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 2. Get xAI API Key

1. Visit [xAI Console](https://console.x.ai/)
2. Create an account or sign in
3. Generate an API key
4. Add it to your `.env` file

## Usage

### Command Line Interface

#### Basic Usage

```bash
export PATH="$HOME/.local/bin:$PATH"

# Analyze a PDF contract
./run_with_env.sh python -m contract_fipo.main --file path/to/contract.pdf

# Analyze a text file
./run_with_env.sh python -m contract_fipo.main --file path/to/contract.txt

# Analyze text directly
./run_with_env.sh python -m contract_fipo.main --text "This is a contract between John Doe and Jane Smith..."

# Save results to a file
./run_with_env.sh python -m contract_fipo.main --file contract.pdf --output results.json
```

#### Database Operations

```bash
export PATH="$HOME/.local/bin:$PATH"

# List all analyzed contracts
./run_with_env.sh python -m contract_fipo.main --list-contracts

# Get specific contract details
./run_with_env.sh python -m contract_fipo.main --get-contract 123

# Test database connection
./run_with_env.sh python -m contract_fipo.main --test-db
```

#### Verbose Output

```bash
# Enable detailed logging
./run_with_env.sh python -m contract_fipo.main --file contract.pdf --verbose
```

### Web API

#### Start the API Server

```bash
export PATH="$HOME/.local/bin:$PATH"

# Development server
./run_with_env.sh uvicorn contract_fipo.api:app --reload --host 0.0.0.0 --port 8000

# Production server
./run_with_env.sh uvicorn contract_fipo.api:app --host 0.0.0.0 --port 8000 --workers 4
```

#### API Endpoints

##### Upload and Parse File

```bash
# Synchronous processing
curl -X POST "http://localhost:8000/parse" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contract.pdf"

# Asynchronous processing
curl -X POST "http://localhost:8000/parse?async_processing=true" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contract.pdf"
```

##### Parse Text Content

```bash
curl -X POST "http://localhost:8000/parse-text" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a contract between John Doe and Jane Smith...",
    "source_identifier": "api_input"
  }'
```

##### List Contracts

```bash
# Get all contracts
curl -X GET "http://localhost:8000/contracts"

# With pagination
curl -X GET "http://localhost:8000/contracts?limit=10&offset=0"
```

##### Get Contract Details

```bash
curl -X GET "http://localhost:8000/contracts/123"
```

##### Delete Contract

```bash
curl -X DELETE "http://localhost:8000/contracts/123"
```

##### Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

#### API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Project Structure

```
contract-fipo/
├── contract_fipo/           # Main package
│   ├── __init__.py
│   ├── main.py             # CLI entry point
│   ├── api.py              # FastAPI application
│   ├── config.py           # Configuration settings
│   ├── parser.py           # Document parsing
│   ├── pii_handler.py      # PII detection and tokenization
│   ├── ai_client.py        # Grok API integration
│   └── db_handler.py       # Database operations
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Test configuration
│   ├── test_parser.py
│   ├── test_pii_handler.py
│   ├── test_ai_client.py
│   ├── test_db_handler.py
│   ├── test_main.py
│   └── test_api.py
├── pyproject.toml          # Poetry configuration
├── .env.template           # Environment template
├── .env                    # Environment variables
└── README.md              # This file
```

### Code Quality Tools

```bash
# Format code
poetry run black contract_fipo/ tests/

# Lint code
poetry run flake8 contract_fipo/ tests/

# Type checking
poetry run mypy contract_fipo/
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes with tests
3. Run test suite: `poetry run pytest`
4. Format and lint code
5. Submit pull request

## Testing

### Run All Tests

```bash
# Run all tests using the environment script
./run_with_env.sh pytest

# Run with coverage
./run_with_env.sh pytest --cov=contract_fipo

# Run specific test file
./run_with_env.sh pytest tests/test_parser.py

# Run with verbose output
./run_with_env.sh pytest -v
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **API Tests**: FastAPI endpoint testing
- **Database Tests**: PostgreSQL integration testing

### Mock Data

Tests use mock data and temporary files to avoid dependencies on external services during testing.

## Deployment

### Using Docker (Recommended)

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY contract_fipo/ ./contract_fipo/

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "contract_fipo.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment-Specific Configuration

Create environment-specific `.env` files:
- `.env.development`
- `.env.staging`
- `.env.production`

### Background Task Processing

For production deployments with high volume:

```bash
# Start Celery worker
poetry run celery -A contract_fipo.tasks worker --loglevel=info

# Start Celery beat (for scheduled tasks)
poetry run celery -A contract_fipo.tasks beat --loglevel=info
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

```bash
# Check PostgreSQL status
brew services list | grep postgresql

# Restart PostgreSQL
brew services restart postgresql@14

# Test connection
poetry run python -m contract_fipo.main --test-db
```

#### 2. xAI API Key Issues

- Verify API key is correct in `.env`
- Check API key permissions
- Ensure sufficient API credits

#### 3. PII Detection Issues

```bash
# Install Presidio dependencies
poetry run pip install presidio-analyzer presidio-anonymizer

# Download spaCy model
poetry run python -m spacy download en_core_web_sm
```

#### 4. PDF Parsing Issues

- Ensure PDF is not password-protected
- Check PDF is not corrupted
- Try with a different PDF file

#### 5. Redis Connection Issues

```bash
# Check Redis status
brew services list | grep redis

# Restart Redis
brew services restart redis

# Test Redis connection
redis-cli ping
```

### Logging

Enable debug logging for troubleshooting:

```bash
# Set in .env file
LOG_LEVEL=DEBUG

# Or use verbose flag
poetry run python -m contract_fipo.main --file contract.pdf --verbose
```

### Performance Optimization

- Use async processing for large files
- Implement database connection pooling
- Configure Redis for optimal performance
- Use CDN for static assets in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Document new features
- Use type hints
- Keep functions focused and small

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

## Changelog

### v0.1.0 (Initial Release)
- PDF and text document parsing
- PII detection and tokenization
- Grok AI integration
- PostgreSQL database storage
- FastAPI web interface
- Comprehensive test suite