"""Pytest configuration and fixtures."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from contract_fipo.config import Settings
from contract_fipo.db_handler import DatabaseHandler, Base
from contract_fipo.parser import DocumentParser
from contract_fipo.pii_handler import PIIHandler
from contract_fipo.ai_client import GrokClient


@pytest.fixture
def test_settings():
    """Test settings fixture."""
    return Settings(
        xai_api_key=os.getenv('XAI_API_KEY', 'test_key'),
        database_url=os.getenv('DATABASE_URL', 'sqlite:///:memory:'),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
        debug=bool(os.getenv('DEBUG', 'True') == 'True'),
        log_level=os.getenv('LOG_LEVEL', 'DEBUG')
    )


@pytest.fixture
def test_db_handler(test_settings):
    """Test database handler with in-memory SQLite."""
    with patch('contract_fipo.db_handler.settings', test_settings):
        db_handler = DatabaseHandler(database_url="sqlite:///:memory:")
        db_handler.create_tables()
        yield db_handler


@pytest.fixture
def document_parser():
    """Document parser fixture."""
    return DocumentParser()


@pytest.fixture
def pii_handler():
    """PII handler fixture."""
    return PIIHandler()


@pytest.fixture
def mock_grok_client():
    """Mock Grok client fixture."""
    with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "key_dates_and_events": [
                {
                    "date": "2024-01-01",
                    "event": "Contract effective date",
                    "importance": "high",
                    "dependencies": []
                }
            ],
            "contract_summary": {
                "contract_type": "Service Agreement",
                "main_parties": ["Party A", "Party B"],
                "primary_purpose": "Test contract"
            }
        }
        '''
        
        mock_client.chat.completions.create.return_value = mock_response
        
        client = GrokClient(api_key="test_key")
        yield client


@pytest.fixture
def sample_contract_text():
    """Sample contract text for testing."""
    return """
    SERVICE AGREEMENT
    
    This Service Agreement ("Agreement") is entered into on January 1, 2024,
    between John Doe (john.doe@email.com) and Jane Smith (jane.smith@company.com).
    
    The parties agree to the following terms:
    
    1. Services: The contractor will provide consulting services.
    2. Payment: $5,000 per month, due on the 15th of each month.
    3. Term: This agreement is effective from January 1, 2024 to December 31, 2024.
    4. Termination: Either party may terminate with 30 days written notice.
    
    Contact Information:
    John Doe: (555) 123-4567
    Jane Smith: (555) 987-6543
    """


@pytest.fixture
def sample_pdf_file():
    """Create a temporary PDF file for testing."""
    # Note: This would require a PDF creation library for a real PDF
    # For testing, we'll create a text file with .pdf extension
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
        f.write("This is a mock PDF content for testing purposes.")
        pdf_path = f.name
    
    yield pdf_path
    
    # Cleanup
    os.unlink(pdf_path)


@pytest.fixture
def sample_text_file():
    """Create a temporary text file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""
        EMPLOYMENT AGREEMENT
        
        This Employment Agreement is between Alice Johnson (alice@company.com)
        and XYZ Corporation, effective March 1, 2024.
        
        Salary: $75,000 annually
        Phone: (555) 111-2222
        """)
        text_path = f.name
    
    yield text_path
    
    # Cleanup
    os.unlink(text_path)