"""Tests for AI client functionality."""

import pytest
import json
from unittest.mock import Mock, patch
from openai import OpenAI

from contract_fipo.ai_client import GrokClient, GrokAPIError


class TestGrokClient:
    """Test cases for GrokClient class."""
    
    def test_initialization(self):
        """Test GrokClient initialization."""
        client = GrokClient(api_key="test_key", base_url="https://test.api.com")
        
        assert client.api_key == "test_key"
        assert client.base_url == "https://test.api.com"
        assert isinstance(client.client, OpenAI)
    
    def test_analyze_contract_success(self, mock_grok_client):
        """Test successful contract analysis."""
        tokenized_text = "This is a test contract with [PII_PERSON_1] and [PII_EMAIL_1]"
        
        result = mock_grok_client.analyze_contract(tokenized_text)
        
        assert isinstance(result, dict)
        assert "key_dates_and_events" in result
        assert "contract_summary" in result
        
        # Verify the mock was called
        mock_grok_client.client.chat.completions.create.assert_called_once()
    
    def test_analyze_contract_with_retry(self):
        """Test contract analysis with retry logic."""
        with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # First call fails, second succeeds
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"test": "success"}'
            
            mock_client.chat.completions.create.side_effect = [
                Exception("API Error"),
                mock_response
            ]
            
            client = GrokClient(api_key="test_key")
            result = client.analyze_contract("test text")
            
            assert result == {"test": "success"}
            assert mock_client.chat.completions.create.call_count == 2
    
    def test_analyze_contract_max_retries_exceeded(self):
        """Test contract analysis when max retries are exceeded."""
        with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # All calls fail
            mock_client.chat.completions.create.side_effect = Exception("Persistent API Error")
            
            client = GrokClient(api_key="test_key")
            
            with pytest.raises(GrokAPIError):
                client.analyze_contract("test text")
    
    def test_analyze_contract_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Invalid JSON response"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            client = GrokClient(api_key="test_key")
            result = client.analyze_contract("test text")
            
            assert "error" in result
            assert "raw_content" in result
            assert result["raw_content"] == "Invalid JSON response"
    
    def test_create_analysis_prompt(self):
        """Test prompt creation for analysis."""
        client = GrokClient(api_key="test_key")
        tokenized_text = "Test contract with [PII_PERSON_1]"
        
        prompt = client._create_analysis_prompt(tokenized_text)
        
        assert isinstance(prompt, str)
        assert tokenized_text in prompt
        assert "JSON" in prompt
        assert "key_dates_and_events" in prompt
        assert "contract_summary" in prompt
        assert "PII tokens" in prompt
    
    def test_prompt_preserves_tokens(self):
        """Test that prompt creation preserves PII tokens."""
        client = GrokClient(api_key="test_key")
        tokenized_text = "Contract between [PII_PERSON_1] and [PII_PERSON_2] for [PII_EMAIL_1]"
        
        prompt = client._create_analysis_prompt(tokenized_text)
        
        assert "[PII_PERSON_1]" in prompt
        assert "[PII_PERSON_2]" in prompt
        assert "[PII_EMAIL_1]" in prompt
    
    def test_api_call_parameters(self):
        """Test that API calls use correct parameters."""
        with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"test": "response"}'
            
            mock_client.chat.completions.create.return_value = mock_response
            
            client = GrokClient(api_key="test_key")
            client.analyze_contract("test text")
            
            # Verify API call parameters
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == "grok-beta"
            assert call_args[1]['temperature'] == 0.1
            assert call_args[1]['max_tokens'] == 4000
            assert len(call_args[1]['messages']) == 2
            assert call_args[1]['messages'][0]['role'] == 'system'
            assert call_args[1]['messages'][1]['role'] == 'user'
    
    def test_different_api_errors(self):
        """Test handling of different types of API errors."""
        with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            client = GrokClient(api_key="test_key")
            
            # Test different error types
            error_types = [
                Exception("Network error"),
                ValueError("Invalid request"),
                KeyError("Missing key"),
            ]
            
            for error in error_types:
                mock_client.chat.completions.create.side_effect = error
                
                with pytest.raises(GrokAPIError):
                    client.analyze_contract("test text")
    
    def test_empty_response_handling(self):
        """Test handling of empty API response."""
        with patch('contract_fipo.ai_client.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = ""
            
            mock_client.chat.completions.create.return_value = mock_response
            
            client = GrokClient(api_key="test_key")
            result = client.analyze_contract("test text")
            
            assert "error" in result
            assert "raw_content" in result