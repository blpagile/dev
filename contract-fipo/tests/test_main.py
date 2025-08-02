"""Tests for main application functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json

from contract_fipo.main import ContractAnalyzer, create_parser


class TestContractAnalyzer:
    """Test cases for ContractAnalyzer class."""
    
    @patch('contract_fipo.main.DatabaseHandler')
    @patch('contract_fipo.main.GrokClient')
    @patch('contract_fipo.main.PIIHandler')
    @patch('contract_fipo.main.DocumentParser')
    def test_analyzer_initialization(self, mock_parser, mock_pii, mock_grok, mock_db):
        """Test ContractAnalyzer initialization."""
        # Mock database table creation
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        analyzer = ContractAnalyzer()
        
        assert analyzer.document_parser is not None
        assert analyzer.pii_handler is not None
        assert analyzer.grok_client is not None
        assert analyzer.db_handler is not None
        
        # Verify database tables were created
        mock_db_instance.create_tables.assert_called_once()
    
    @patch('contract_fipo.main.DatabaseHandler')
    @patch('contract_fipo.main.GrokClient')
    @patch('contract_fipo.main.PIIHandler')
    @patch('contract_fipo.main.DocumentParser')
    def test_analyze_file_success(self, mock_parser_class, mock_pii_class, mock_grok_class, mock_db_class):
        """Test successful file analysis."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = "Parsed contract text"
        mock_parser_class.return_value = mock_parser
        
        ai_response_for_mock = {"contract_summary": {"type": "Service Agreement"}}

        mock_pii = Mock()
        mock_pii.tokenize_text.return_value = ("Tokenized text", {"[PII_PERSON_1]": "John Doe"})
        # Mock the detokenize call that happens internally
        mock_pii.detokenize_text.return_value = json.dumps(ai_response_for_mock)
        mock_pii_class.return_value = mock_pii
        
        mock_grok = Mock()
        mock_grok.analyze_contract.return_value = ai_response_for_mock
        mock_grok_class.return_value = mock_grok
        
        mock_db = Mock()
        # This mock is for the __init__ call
        mock_db.create_tables.return_value = None
        mock_db.save_parsed_contract.return_value = 123
        mock_db_class.return_value = mock_db
        
        analyzer = ContractAnalyzer()
        result = analyzer.analyze_file("test_contract.pdf")
        
        assert result["success"] is True
        assert result["contract_id"] == 123
        assert "analysis" in result
        assert result["pii_entities_found"] == 1
        
        # Verify all components were called
        mock_parser.parse_file.assert_called_once_with("test_contract.pdf")
        mock_pii.tokenize_text.assert_called_once()
        mock_grok.analyze_contract.assert_called_once()
        mock_db.save_parsed_contract.assert_called_once()
    
    @patch('contract_fipo.main.DatabaseHandler')
    @patch('contract_fipo.main.GrokClient')
    @patch('contract_fipo.main.PIIHandler')
    @patch('contract_fipo.main.DocumentParser')
    def test_analyze_file_parser_error(self, mock_parser_class, mock_pii_class, mock_grok_class, mock_db_class):
        """Test file analysis with parser error."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.parse_file.side_effect = FileNotFoundError("File not found")
        mock_parser_class.return_value = mock_parser
        
        mock_db = Mock()
        mock_db.create_tables.return_value = None
        mock_db_class.return_value = mock_db
        
        analyzer = ContractAnalyzer()
        result = analyzer.analyze_file("nonexistent.pdf")
        
        assert result["success"] is False
        assert "File not found" in result["error"]
    
    @patch('contract_fipo.main.DatabaseHandler')
    @patch('contract_fipo.main.GrokClient')
    @patch('contract_fipo.main.PIIHandler')
    @patch('contract_fipo.main.DocumentParser')
    def test_analyze_text_success(self, mock_parser_class, mock_pii_class, mock_grok_class, mock_db_class):
        """Test successful text analysis."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.parse_text.return_value = "Cleaned contract text"
        mock_parser_class.return_value = mock_parser
        
        ai_response_for_mock = {"contract_summary": {"type": "Employment Agreement"}}

        mock_pii = Mock()
        mock_pii.tokenize_text.return_value = ("Tokenized text", {"[PII_EMAIL_1]": "test@example.com"})
        mock_pii.detokenize_text.return_value = json.dumps(ai_response_for_mock)
        mock_pii_class.return_value = mock_pii
        
        mock_grok = Mock()
        mock_grok.analyze_contract.return_value = ai_response_for_mock
        mock_grok_class.return_value = mock_grok
        
        mock_db = Mock()
        # This mock is for the __init__ call
        mock_db.create_tables.return_value = None
        mock_db.save_parsed_contract.return_value = 456
        mock_db_class.return_value = mock_db
        
        analyzer = ContractAnalyzer()
        result = analyzer.analyze_text("Contract text content", "test_source")
        
        assert result["success"] is True
        assert result["contract_id"] == 456
        assert "analysis" in result
        assert result["pii_entities_found"] == 1
        
        # Verify components were called correctly
        mock_parser.parse_text.assert_called_once_with("Contract text content")
        mock_pii.tokenize_text.assert_called_once()
        mock_grok.analyze_contract.assert_called_once()
        mock_db.save_parsed_contract.assert_called_once()
    
    @patch('contract_fipo.main.DatabaseHandler')
    @patch('contract_fipo.main.GrokClient')
    @patch('contract_fipo.main.PIIHandler')
    @patch('contract_fipo.main.DocumentParser')
    def test_detokenize_response(self, mock_parser_class, mock_pii_class, mock_grok_class, mock_db_class):
        """Test response detokenization."""
        mock_pii = Mock()
        mock_pii.detokenize_text.return_value = '{"name": "John Doe", "email": "john@example.com"}'
        mock_pii_class.return_value = mock_pii
        
        mock_db = Mock()
        mock_db.create_tables.return_value = None
        mock_db_class.return_value = mock_db
        
        analyzer = ContractAnalyzer()
        
        response = {"name": "[PII_PERSON_1]", "email": "[PII_EMAIL_1]"}
        token_mapping = {"[PII_PERSON_1]": "John Doe", "[PII_EMAIL_1]": "john@example.com"}
        
        result = analyzer._detokenize_response(response, token_mapping)
        
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
    
    def test_empty_text_handling(self):
        """Test handling of empty text input."""
        with patch('contract_fipo.main.DatabaseHandler') as mock_db_class:
            mock_db = Mock()
            mock_db.create_tables.return_value = None
            mock_db_class.return_value = mock_db
            
            analyzer = ContractAnalyzer()
            result = analyzer.analyze_text("", "empty_test")
            
            assert result["success"] is False
            assert "No text content provided" in result["error"]


class TestArgumentParser:
    """Test cases for argument parser."""
    
    def test_create_parser(self):
        """Test argument parser creation."""
        parser = create_parser()
        
        assert parser is not None
        assert parser.description is not None
    
    def test_file_argument(self):
        """Test file argument parsing."""
        parser = create_parser()
        args = parser.parse_args(['--file', 'test.pdf'])
        
        assert args.file == 'test.pdf'
        assert args.text is None
    
    def test_text_argument(self):
        """Test text argument parsing."""
        parser = create_parser()
        args = parser.parse_args(['--text', 'Contract content'])
        
        assert args.text == 'Contract content'
        assert args.file is None
    
    def test_mutually_exclusive_arguments(self):
        """Test that file and text arguments are mutually exclusive."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(['--file', 'test.pdf', '--text', 'content'])
    
    def test_database_arguments(self):
        """Test database-related arguments."""
        parser = create_parser()
        
        # Test list contracts
        args = parser.parse_args(['--list-contracts'])
        assert args.list_contracts is True
        
        # Test get contract
        args = parser.parse_args(['--get-contract', '123'])
        assert args.get_contract == 123
    
    def test_utility_arguments(self):
        """Test utility arguments."""
        parser = create_parser()
        
        # Test database test
        args = parser.parse_args(['--test-db'])
        assert args.test_db is True
        
        # Test verbose
        args = parser.parse_args(['--file', 'test.pdf', '--verbose'])
        assert args.verbose is True
    
    def test_required_arguments(self):
        """Test that at least one main argument is required."""
        parser = create_parser()
        
        # Should work with valid arguments
        valid_args = [
            ['--file', 'test.pdf'],
            ['--text', 'content'],
            ['--list-contracts'],
            ['--get-contract', '123'],
            ['--test-db']
        ]
        
        for args in valid_args:
            try:
                parser.parse_args(args)
            except SystemExit:
                pytest.fail(f"Valid arguments {args} should not raise SystemExit")
        
        # Should fail without any arguments
        with pytest.raises(SystemExit):
            parser.parse_args([])