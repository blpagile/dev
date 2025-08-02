"""FastAPI web application for contract analysis."""

import logging
import asyncio
from typing import Optional, List
from pathlib import Path
import tempfile
import os

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .main import ContractAnalyzer
from .db_handler import DatabaseHandler, ParsedContract
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="Contract FIPO API",
    description="Contract analysis tool with PII detection and Grok AI integration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global analyzer instance
analyzer = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global analyzer
    try:
        analyzer = ContractAnalyzer()
        logger.info("Contract analyzer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize contract analyzer: {e}")
        raise


# Pydantic models for API requests/responses
class TextAnalysisRequest(BaseModel):
    """Request model for text analysis."""
    text: str
    source_identifier: Optional[str] = "api_input"


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""
    success: bool
    contract_id: Optional[int] = None
    analysis: Optional[dict] = None
    pii_entities_found: Optional[int] = None
    error: Optional[str] = None


class ContractListResponse(BaseModel):
    """Response model for contract list."""
    contracts: List[dict]
    total: int


class ContractDetailResponse(BaseModel):
    """Response model for contract details."""
    id: int
    original_file: str
    created_at: str
    analysis: dict
    pii_entities_found: int


# Dependency to get database handler
def get_db_handler() -> DatabaseHandler:
    """Get database handler instance."""
    return analyzer.db_handler if analyzer else None


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Contract FIPO API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if analyzer and analyzer.db_handler.test_connection():
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "unhealthy", "database": "disconnected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.post("/parse", response_model=AnalysisResponse)
async def parse_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    async_processing: bool = False
):
    """
    Parse and analyze a contract file.
    
    Args:
        file: Uploaded contract file (PDF or text)
        async_processing: Whether to process asynchronously
        
    Returns:
        Analysis results
    """
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    
    # Validate file type
    allowed_extensions = {'.pdf', '.txt', '.text'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Saved uploaded file to: {temp_file_path}")
        
        if async_processing:
            # Process asynchronously
            background_tasks.add_task(
                _process_file_async,
                temp_file_path,
                file.filename
            )
            return AnalysisResponse(
                success=True,
                contract_id=None,
                analysis={"message": "Processing started asynchronously"},
                pii_entities_found=None
            )
        else:
            # Process synchronously
            result = analyzer.analyze_file(temp_file_path)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            return AnalysisResponse(**result)
    
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        # Clean up temp file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse-text", response_model=AnalysisResponse)
async def parse_text(request: TextAnalysisRequest):
    """
    Parse and analyze contract text directly.
    
    Args:
        request: Text analysis request
        
    Returns:
        Analysis results
    """
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    
    try:
        result = analyzer.analyze_text(request.text, request.source_identifier)
        return AnalysisResponse(**result)
    
    except Exception as e:
        logger.error(f"Text processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contracts", response_model=ContractListResponse)
async def list_contracts(
    limit: int = 10,
    offset: int = 0,
    db_handler: DatabaseHandler = Depends(get_db_handler)
):
    """
    List all analyzed contracts with pagination.
    
    Args:
        limit: Maximum number of contracts to return
        offset: Number of contracts to skip
        db_handler: Database handler dependency
        
    Returns:
        List of contracts
    """
    if not db_handler:
        raise HTTPException(status_code=500, detail="Database handler not available")
    
    try:
        contracts = db_handler.get_all_contracts(limit=limit, offset=offset)
        
        contract_list = []
        for contract in contracts:
            contract_list.append({
                "id": contract.id,
                "original_file": contract.original_file,
                "created_at": contract.created_at.isoformat(),
                "pii_entities_found": len(contract.token_mapping) if contract.token_mapping else 0
            })
        
        return ContractListResponse(
            contracts=contract_list,
            total=len(contract_list)
        )
    
    except Exception as e:
        logger.error(f"Failed to list contracts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contracts/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: int,
    db_handler: DatabaseHandler = Depends(get_db_handler)
):
    """
    Get detailed information about a specific contract.
    
    Args:
        contract_id: Contract ID
        db_handler: Database handler dependency
        
    Returns:
        Contract details
    """
    if not db_handler:
        raise HTTPException(status_code=500, detail="Database handler not available")
    
    try:
        contract = db_handler.get_contract_by_id(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        return ContractDetailResponse(
            id=contract.id,
            original_file=contract.original_file,
            created_at=contract.created_at.isoformat(),
            analysis=contract.detokenized_response,
            pii_entities_found=len(contract.token_mapping) if contract.token_mapping else 0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/contracts/{contract_id}")
async def delete_contract(
    contract_id: int,
    db_handler: DatabaseHandler = Depends(get_db_handler)
):
    """
    Delete a specific contract.
    
    Args:
        contract_id: Contract ID
        db_handler: Database handler dependency
        
    Returns:
        Deletion confirmation
    """
    if not db_handler:
        raise HTTPException(status_code=500, detail="Database handler not available")
    
    try:
        success = db_handler.delete_contract(contract_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        return {"message": f"Contract {contract_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_file_async(file_path: str, original_filename: str):
    """
    Process a file asynchronously in the background.
    
    Args:
        file_path: Path to the temporary file
        original_filename: Original filename
    """
    try:
        logger.info(f"Starting async processing of: {original_filename}")
        
        # Run the analysis in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            analyzer.analyze_file,
            file_path
        )
        
        logger.info(f"Async processing completed for: {original_filename}")
        logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"Async processing failed for {original_filename}: {e}")
    
    finally:
        # Clean up temp file
        try:
            os.unlink(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to clean up temp file {file_path}: {e}")


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "contract_fipo.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )