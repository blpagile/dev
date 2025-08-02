"""Tests for document parsing functionality."""

import pytest
import tempfile
import os
from pathlib import Path

from contract_fipo.parser import DocumentParser


class TestDocumentParser:
    """Test cases for DocumentParser class."""
    
    def test_parse_text_file(self, document_parser, sample_text_file):
        """Test parsing a text file."""
        result = document_parser.parse_file(sample_text_file)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "EMPLOYMENT AGREEMENT" in result
        assert "alice@company.com" in result
    
    def test_parse_text_string(self, document_parser, sample_contract_text):
        """Test parsing raw text content."""
        result = document_parser.parse_text(sample_contract_text)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "SERVICE AGREEMENT" in result
        assert "john.doe@email.com" in result
    
    def test_file_not_found(self, document_parser):
        """Test handling of non-existent files."""
        with pytest.raises(FileNotFoundError):
            document_parser.parse_file("non_existent_file.txt")
    
    def test_unsupported_file_type(self, document_parser):
        """Test handling of unsupported file types."""
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                document_parser.parse_file(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_empty_text_handling(self, document_parser):
        """Test handling of empty text."""
        result = document_parser.parse_text("")
        assert result == ""
        
        result = document_parser.parse_text("   ")
        assert result == ""
    
    def test_text_cleaning(self, document_parser):
        """Test text cleaning functionality."""
        messy_text = "  This   has    excessive   whitespace  \n\n\n  and   newlines  "
        result = document_parser._clean_text(messy_text)
        
        assert "excessive" in result
        assert "   " not in result  # No triple spaces
        assert result.strip() == result  # No leading/trailing whitespace
    
    def test_special_character_removal(self, document_parser):
        """Test removal of special characters."""
        text_with_special_chars = "Normal text\x00\x08\x0b\x0c\x0e\x1f\x7f\x9fmore text"
        result = document_parser._clean_text(text_with_special_chars)
        
        assert "\x00" not in result
        assert "\x08" not in result
        assert "Normal text more text" in result
    
    def test_unicode_handling(self, document_parser):
        """Test handling of Unicode characters."""
        unicode_text = "Contract with unicode: café, naïve, résumé"
        result = document_parser.parse_text(unicode_text)
        
        assert "café" in result
        assert "naïve" in result
        assert "résumé" in result
    
    def test_large_text_handling(self, document_parser):
        """Test handling of large text content."""
        large_text = "This is a test sentence. " * 10000  # ~250KB of text
        result = document_parser.parse_text(large_text)
        
        assert len(result) > 0
        assert "This is a test sentence." in result