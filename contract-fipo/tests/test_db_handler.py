"""Tests for database handler functionality."""

import pytest
from datetime import datetime

from contract_fipo.db_handler import DatabaseHandler, ParsedContract


class TestDatabaseHandler:
    """Test cases for DatabaseHandler class."""
    
    def test_create_tables(self, test_db_handler):
        """Test database table creation."""
        # Tables should already be created by the fixture
        assert test_db_handler.test_connection()
    
    def test_save_and_retrieve_contract(self, test_db_handler):
        """Test saving and retrieving a contract."""
        # Test data
        original_file = "test_contract.pdf"
        tokenized_text = "Contract between [PII_PERSON_1] and [PII_PERSON_2]"
        ai_response = {
            "contract_summary": {
                "contract_type": "Service Agreement",
                "main_parties": ["[PII_PERSON_1]", "[PII_PERSON_2]"]
            }
        }
        detokenized_response = {
            "contract_summary": {
                "contract_type": "Service Agreement",
                "main_parties": ["John Doe", "Jane Smith"]
            }
        }
        token_mapping = {
            "[PII_PERSON_1]": "John Doe",
            "[PII_PERSON_2]": "Jane Smith"
        }
        
        # Save contract
        contract_id = test_db_handler.save_parsed_contract(
            original_file=original_file,
            tokenized_text=tokenized_text,
            ai_response=ai_response,
            detokenized_response=detokenized_response,
            token_mapping=token_mapping
        )
        
        assert isinstance(contract_id, int)
        assert contract_id > 0
        
        # Retrieve contract
        retrieved_contract = test_db_handler.get_contract_by_id(contract_id)
        
        assert retrieved_contract is not None
        assert retrieved_contract.id == contract_id
        assert retrieved_contract.original_file == original_file
        assert retrieved_contract.tokenized_text == tokenized_text
        assert retrieved_contract.ai_response == ai_response
        assert retrieved_contract.detokenized_response == detokenized_response
        assert retrieved_contract.token_mapping == token_mapping
        assert isinstance(retrieved_contract.created_at, datetime)
    
    def test_get_nonexistent_contract(self, test_db_handler):
        """Test retrieving a non-existent contract."""
        result = test_db_handler.get_contract_by_id(99999)
        assert result is None
    
    def test_get_all_contracts(self, test_db_handler):
        """Test retrieving all contracts with pagination."""
        # Save multiple contracts
        contracts_data = [
            ("contract1.pdf", "Text 1", {"data": "response1"}, {"data": "detokenized1"}, {}),
            ("contract2.pdf", "Text 2", {"data": "response2"}, {"data": "detokenized2"}, {}),
            ("contract3.pdf", "Text 3", {"data": "response3"}, {"data": "detokenized3"}, {}),
        ]
        
        saved_ids = []
        for original_file, tokenized_text, ai_response, detokenized_response, token_mapping in contracts_data:
            contract_id = test_db_handler.save_parsed_contract(
                original_file=original_file,
                tokenized_text=tokenized_text,
                ai_response=ai_response,
                detokenized_response=detokenized_response,
                token_mapping=token_mapping
            )
            saved_ids.append(contract_id)
        
        # Test getting all contracts
        all_contracts = test_db_handler.get_all_contracts()
        assert len(all_contracts) == 3
        
        # Test pagination
        first_two = test_db_handler.get_all_contracts(limit=2)
        assert len(first_two) == 2
        
        remaining = test_db_handler.get_all_contracts(limit=10, offset=2)
        assert len(remaining) == 1
        
        # Verify order (should be newest first)
        assert all_contracts[0].created_at >= all_contracts[1].created_at
        assert all_contracts[1].created_at >= all_contracts[2].created_at
    
    def test_delete_contract(self, test_db_handler):
        """Test deleting a contract."""
        # Save a contract first
        contract_id = test_db_handler.save_parsed_contract(
            original_file="test_delete.pdf",
            tokenized_text="Test text",
            ai_response={"test": "data"},
            detokenized_response={"test": "data"},
            token_mapping={}
        )
        
        # Verify it exists
        contract = test_db_handler.get_contract_by_id(contract_id)
        assert contract is not None
        
        # Delete it
        success = test_db_handler.delete_contract(contract_id)
        assert success is True
        
        # Verify it's gone
        contract = test_db_handler.get_contract_by_id(contract_id)
        assert contract is None
    
    def test_delete_nonexistent_contract(self, test_db_handler):
        """Test deleting a non-existent contract."""
        success = test_db_handler.delete_contract(99999)
        assert success is False
    
    def test_database_connection_test(self, test_db_handler):
        """Test database connection testing."""
        assert test_db_handler.test_connection() is True
    
    def test_session_management(self, test_db_handler):
        """Test database session management."""
        session = test_db_handler.get_session()
        assert session is not None
        
        # Test that we can execute a query
        result = session.execute("SELECT 1").fetchone()
        assert result[0] == 1
        
        session.close()
    
    def test_contract_model_representation(self, test_db_handler):
        """Test ParsedContract model string representation."""
        contract_id = test_db_handler.save_parsed_contract(
            original_file="very_long_filename_that_should_be_truncated_in_repr.pdf",
            tokenized_text="Test text",
            ai_response={"test": "data"},
            detokenized_response={"test": "data"},
            token_mapping={}
        )
        
        contract = test_db_handler.get_contract_by_id(contract_id)
        repr_str = repr(contract)
        
        assert "ParsedContract" in repr_str
        assert str(contract_id) in repr_str
        assert "very_long_filename_that_should_be_truncated_in_repr" in repr_str
    
    def test_save_contract_with_complex_data(self, test_db_handler):
        """Test saving contract with complex JSON data."""
        complex_ai_response = {
            "key_dates_and_events": [
                {
                    "date": "2024-01-01",
                    "event": "Contract start",
                    "importance": "high",
                    "dependencies": []
                }
            ],
            "contract_summary": {
                "contract_type": "Service Agreement",
                "main_parties": ["Party A", "Party B"],
                "governing_law": "California"
            },
            "risk_assessment": {
                "high_risk_items": ["Termination clause"],
                "recommendations": ["Review termination terms"]
            }
        }
        
        complex_token_mapping = {
            "[PII_PERSON_1]": "John Doe",
            "[PII_EMAIL_1]": "john@example.com",
            "[PII_PHONE_1]": "(555) 123-4567"
        }
        
        contract_id = test_db_handler.save_parsed_contract(
            original_file="complex_contract.pdf",
            tokenized_text="Complex tokenized text",
            ai_response=complex_ai_response,
            detokenized_response=complex_ai_response,  # Same for test
            token_mapping=complex_token_mapping
        )
        
        retrieved_contract = test_db_handler.get_contract_by_id(contract_id)
        
        assert retrieved_contract.ai_response == complex_ai_response
        assert retrieved_contract.token_mapping == complex_token_mapping
        assert "key_dates_and_events" in retrieved_contract.ai_response
        assert len(retrieved_contract.token_mapping) == 3