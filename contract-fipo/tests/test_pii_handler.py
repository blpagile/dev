"""Tests for PII detection and tokenization functionality."""

import pytest
from unittest.mock import patch, Mock

from contract_fipo.pii_handler import PIIHandler


class TestPIIHandler:
    """Test cases for PIIHandler class."""
    
    def test_tokenize_and_detokenize_with_presidio(self, pii_handler):
        """Test PII tokenization and detokenization with Presidio."""
        text = "Contact John Doe at john.doe@email.com or call (555) 123-4567"
        
        # Mock Presidio analyzer results
        mock_results = [
            Mock(start=8, end=16, entity_type='PERSON'),  # John Doe
            Mock(start=20, end=39, entity_type='EMAIL_ADDRESS'),  # john.doe@email.com
            Mock(start=48, end=62, entity_type='PHONE_NUMBER')  # (555) 123-4567
        ]
        
        with patch.object(pii_handler.analyzer, 'analyze', return_value=mock_results):
            tokenized_text, token_mapping = pii_handler.tokenize_text(text)
            
            # Check that PII was tokenized
            assert "John Doe" not in tokenized_text
            assert "john.doe@email.com" not in tokenized_text
            assert "(555) 123-4567" not in tokenized_text
            
            # Check that tokens were created
            assert "[PII_PERSON_1]" in tokenized_text
            assert "[PII_EMAIL_ADDRESS_1]" in tokenized_text
            assert "[PII_PHONE_NUMBER_1]" in tokenized_text
            
            # Check token mapping
            assert len(token_mapping) == 3
            assert "John Doe" in token_mapping.values()
            assert "john.doe@email.com" in token_mapping.values()
            assert "(555) 123-4567" in token_mapping.values()
            
            # Test detokenization
            detokenized_text = pii_handler.detokenize_text(tokenized_text, token_mapping)
            assert detokenized_text == text
    
    def test_tokenize_with_regex_fallback(self):
        """Test PII tokenization with regex fallback."""
        # Create handler without Presidio
        pii_handler = PIIHandler()
        pii_handler.use_presidio = False
        
        text = "Email me at test@example.com or call 555-123-4567"
        tokenized_text, token_mapping = pii_handler.tokenize_text(text)
        
        # Check that email and phone were tokenized
        assert "test@example.com" not in tokenized_text
        assert "555-123-4567" not in tokenized_text
        assert "[PII_EMAIL_1]" in tokenized_text
        assert "[PII_PHONE_1]" in tokenized_text
        
        # Check token mapping
        assert len(token_mapping) >= 2
        assert "test@example.com" in token_mapping.values()
        assert "555-123-4567" in token_mapping.values()
    
    def test_multiple_same_type_entities(self, pii_handler):
        """Test handling multiple entities of the same type."""
        text = "Contact alice@company.com and bob@company.com for details"
        
        # Mock Presidio results for two emails
        mock_results = [
            Mock(start=8, end=25, entity_type='EMAIL_ADDRESS'),  # alice@company.com
            Mock(start=30, end=45, entity_type='EMAIL_ADDRESS')  # bob@company.com
        ]
        
        with patch.object(pii_handler.analyzer, 'analyze', return_value=mock_results):
            tokenized_text, token_mapping = pii_handler.tokenize_text(text)
            
            # Check that both emails were tokenized with different tokens
            assert "[PII_EMAIL_ADDRESS_1]" in tokenized_text
            assert "[PII_EMAIL_ADDRESS_2]" in tokenized_text
            assert "alice@company.com" not in tokenized_text
            assert "bob@company.com" not in tokenized_text
            
            # Check token mapping has both emails
            assert len(token_mapping) == 2
            assert "alice@company.com" in token_mapping.values()
            assert "bob@company.com" in token_mapping.values()
    
    def test_empty_text_handling(self, pii_handler):
        """Test handling of empty text."""
        tokenized_text, token_mapping = pii_handler.tokenize_text("")
        
        assert tokenized_text == ""
        assert len(token_mapping) == 0
    
    def test_text_without_pii(self, pii_handler):
        """Test handling of text without PII."""
        text = "This is a simple contract without any personal information."
        
        with patch.object(pii_handler.analyzer, 'analyze', return_value=[]):
            tokenized_text, token_mapping = pii_handler.tokenize_text(text)
            
            assert tokenized_text == text
            assert len(token_mapping) == 0
    
    def test_regex_patterns(self):
        """Test individual regex patterns."""
        pii_handler = PIIHandler()
        pii_handler.use_presidio = False
        
        test_cases = [
            ("Email: user@domain.com", "EMAIL"),
            ("Phone: (555) 123-4567", "PHONE"),
            ("Phone: 555-123-4567", "PHONE"),
            ("Phone: 555.123.4567", "PHONE"),
            ("SSN: 123-45-6789", "SSN"),
            ("IP: 192.168.1.1", "IP_ADDRESS"),
            ("URL: https://example.com", "URL"),
            ("Name: John Smith", "PERSON"),
        ]
        
        for text, expected_type in test_cases:
            tokenized_text, token_mapping = pii_handler.tokenize_text(text)
            
            # Should have at least one token of the expected type
            assert any(expected_type in token for token in token_mapping.keys())
    
    def test_detokenize_partial_mapping(self, pii_handler):
        """Test detokenization with partial token mapping."""
        text = "Contact [PII_PERSON_1] at [PII_EMAIL_1] or [PII_PHONE_1]"
        partial_mapping = {
            "[PII_PERSON_1]": "John Doe",
            "[PII_EMAIL_1]": "john@example.com"
            # Missing phone mapping
        }
        
        result = pii_handler.detokenize_text(text, partial_mapping)
        
        assert "John Doe" in result
        assert "john@example.com" in result
        assert "[PII_PHONE_1]" in result  # Should remain as token
    
    def test_token_generation_uniqueness(self, pii_handler):
        """Test that generated tokens are unique."""
        # Clear any existing mappings
        pii_handler.token_mapping.clear()
        pii_handler.token_counters.clear()
        
        token1 = pii_handler._generate_token("PERSON", "John Doe")
        token2 = pii_handler._generate_token("PERSON", "Jane Smith")
        token3 = pii_handler._generate_token("EMAIL", "test@example.com")
        
        assert token1 != token2
        assert token1 != token3
        assert token2 != token3
        
        assert "PERSON_1" in token1
        assert "PERSON_2" in token2
        assert "EMAIL_1" in token3
    
    def test_presidio_initialization_failure(self):
        """Test fallback when Presidio initialization fails."""
        with patch('contract_fipo.pii_handler.AnalyzerEngine', side_effect=Exception("Presidio not available")):
            pii_handler = PIIHandler()
            
            assert not pii_handler.use_presidio
            
            # Should still work with regex
            text = "Email: test@example.com"
            tokenized_text, token_mapping = pii_handler.tokenize_text(text)
            
            assert "test@example.com" not in tokenized_text
            assert len(token_mapping) > 0