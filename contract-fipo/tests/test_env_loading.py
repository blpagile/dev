"""Test to verify environment variables are loaded from .env file."""

import os
import pytest
from contract_fipo.config import Settings

@pytest.fixture
def settings():
    """Get settings instance for testing."""
    return Settings()

def test_env_variable_loading(settings):
    """Test if XAI_API_KEY is loaded from .env or uses fallback."""
    api_key = settings.xai_api_key
    env_api_key = os.getenv('XAI_API_KEY', 'test_key')
    assert api_key == env_api_key, f"Expected API key {env_api_key}, but got {api_key}"
    print(f"Loaded API Key: {api_key}")
