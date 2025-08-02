"""Tests for FastAPI application."""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, create_autospec
from fastapi.testclient import TestClient

from contract_fipo.api import app
from contract_fipo.main import ContractAnalyzer


@pytest.fixture
def client():
    print(f"Using TestClient from: {TestClient.__module__}.{TestClient.__name__}")
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_analyzer():
    """Mock analyzer fixture."""
    # Using autospec=True ensures the mock has the same methods/attributes
    # as the real ContractAnalyzer class, making tests more robust.
    mock_instance = create_autospec(ContractAnalyzer, instance=True)

    mock_instance.db_handler.test_connection.return_value = True
    mock_instance.analyze_file.return_value = {
        "success": True,
        "contract_id": 123,
        "analysis": {"contract_summary": {"type": "Test Contract"}},
        "pii_entities_found": 2
    }
    mock_instance.analyze_text.return_value = {
        "success": True,
        "contract_id": 124,
        "analysis": {"contract_summary": {"type": "Text Contract"}},
        "pii_entities_found": 1
    }
    return mock_instance


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "Contract FIPO API"
    
    def test_health_check_healthy(self, client, mock_analyzer):
        """Test health check when system is healthy."""
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
    
    def test_health_check_unhealthy(self, client):
        """Test health check when system is unhealthy."""
        with patch('contract_fipo.api.analyzer', None):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database"] == "disconnected"
    
    def test_parse_file_success(self, client, mock_analyzer):
        """Test successful file parsing."""
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            # Create a temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Test contract content")
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    response = client.post(
                        "/parse",
                        files={"file": ("test.txt", f, "text/plain")}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["contract_id"] == 123
                assert "analysis" in data
                assert data["pii_entities_found"] == 2
            
            finally:
                os.unlink(temp_path)
    
    def test_parse_file_unsupported_type(self, client, mock_analyzer):
        """Test parsing unsupported file type."""
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            # Create a file with unsupported extension
            with tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False) as f:
                f.write("Test content")
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    response = client.post(
                        "/parse",
                        files={"file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                    )
                
                assert response.status_code == 400
                data = response.json()
                assert "Unsupported file type" in data["detail"]
            
            finally:
                os.unlink(temp_path)
    
    def test_parse_file_async(self, client, mock_analyzer):
        """Test asynchronous file parsing."""
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Test contract content")
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    response = client.post(
                        "/parse?async_processing=true",
                        files={"file": ("test.txt", f, "text/plain")}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "Processing started asynchronously" in data["analysis"]["message"]
            
            finally:
                # File should be cleaned up by background task
                pass
    
    def test_parse_text_success(self, client, mock_analyzer):
        """Test successful text parsing."""
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            request_data = {
                "text": "This is a test contract with John Doe",
                "source_identifier": "test_input"
            }
            
            response = client.post("/parse-text", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["contract_id"] == 124
            assert "analysis" in data
            assert data["pii_entities_found"] == 1
    
    def test_parse_text_missing_text(self, client, mock_analyzer):
        """Test text parsing with missing text field."""
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            request_data = {"source_identifier": "test_input"}
            
            response = client.post("/parse-text", json=request_data)
            
            assert response.status_code == 422  # Validation error
    
    def test_list_contracts(self, client, mock_analyzer):
        """Test listing contracts."""
        # Mock database handler
        mock_contracts = [
            Mock(
                id=1,
                original_file="contract1.pdf",
                created_at=Mock(),
                token_mapping={"[PII_PERSON_1]": "John Doe"}
            ),
            Mock(
                id=2,
                original_file="contract2.pdf",
                created_at=Mock(),
                token_mapping={}
            )
        ]
        mock_contracts[0].created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_contracts[1].created_at.isoformat.return_value = "2024-01-02T00:00:00"
        
        mock_analyzer.db_handler.get_all_contracts.return_value = mock_contracts
        
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.get("/contracts")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["contracts"]) == 2
            assert data["total"] == 2
            assert data["contracts"][0]["id"] == 1
            assert data["contracts"][0]["pii_entities_found"] == 1
            assert data["contracts"][1]["pii_entities_found"] == 0
    
    def test_list_contracts_with_pagination(self, client, mock_analyzer):
        """Test listing contracts with pagination."""
        mock_contracts = [Mock(id=i, original_file=f"contract{i}.pdf", created_at=Mock(), token_mapping={}) for i in range(5)]
        for contract in mock_contracts:
            contract.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        mock_analyzer.db_handler.get_all_contracts.return_value = mock_contracts[:3]  # Return first 3
        
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.get("/contracts?limit=3&offset=0")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["contracts"]) == 3
    
    def test_get_contract_success(self, client, mock_analyzer):
        """Test getting a specific contract."""
        mock_contract = Mock(
            id=123,
            original_file="test_contract.pdf",
            created_at=Mock(),
            detokenized_response={"contract_summary": {"type": "Service Agreement"}},
            token_mapping={"[PII_PERSON_1]": "John Doe"}
        )
        mock_contract.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        mock_analyzer.db_handler.get_contract_by_id.return_value = mock_contract
        
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.get("/contracts/123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 123
            assert data["original_file"] == "test_contract.pdf"
            assert data["pii_entities_found"] == 1
            assert "analysis" in data
    
    def test_get_contract_not_found(self, client, mock_analyzer):
        """Test getting a non-existent contract."""
        mock_analyzer.db_handler.get_contract_by_id.return_value = None
        
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.get("/contracts/999")
            
            assert response.status_code == 404
            data = response.json()
            assert "Contract not found" in data["detail"]
    
    def test_delete_contract_success(self, client, mock_analyzer):
        """Test successful contract deletion."""
        mock_analyzer.db_handler.delete_contract.return_value = True
        
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.delete("/contracts/123")
            
            assert response.status_code == 200
            data = response.json()
            assert "deleted successfully" in data["message"]
    
    def test_delete_contract_not_found(self, client, mock_analyzer):
        """Test deleting a non-existent contract."""
        mock_analyzer.db_handler.delete_contract.return_value = False
        
        with patch('contract_fipo.api.analyzer', mock_analyzer):
            response = client.delete("/contracts/999")
            
            assert response.status_code == 404
            data = response.json()
            assert "Contract not found" in data["detail"]
    
    def test_analyzer_not_initialized(self, client):
        """Test API behavior when analyzer is not initialized."""
        with patch('contract_fipo.api.analyzer', None):
            response = client.post("/parse-text", json={"text": "test"})
            
            assert response.status_code == 500
            data = response.json()
            assert "Analyzer not initialized" in data["detail"]
    
    def test_database_handler_not_available(self, client):
        """Test API behavior when database handler is not available."""
        with patch('contract_fipo.api.get_db_handler', return_value=None):
            response = client.get("/contracts")
            
            assert response.status_code == 500
            data = response.json()
            assert "Database handler not available" in data["detail"]