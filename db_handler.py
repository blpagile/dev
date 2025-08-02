"""Database models and handlers using SQLAlchemy."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class ParsedContract(Base):
    """Database model for parsed contracts."""
    
    __tablename__ = 'parsed_contracts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_file = Column(Text, nullable=False)
    tokenized_text = Column(Text, nullable=False)
    ai_response = Column(JSON, nullable=False)
    detokenized_response = Column(JSON, nullable=False)
    token_mapping = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ParsedContract(id={self.id}, file='{self.original_file[:50]}...', created_at='{self.created_at}')>"


class DatabaseHandler:
    """Handles database operations for contract analysis."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the database handler.
        
        Args:
            database_url: Database connection URL (defaults to settings)
        """
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"Initialized database handler with URL: {self.database_url}")
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Successfully created database tables")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def save_parsed_contract(
        self,
        original_file: str,
        tokenized_text: str,
        ai_response: Dict[str, Any],
        detokenized_response: Dict[str, Any],
        token_mapping: Dict[str, str]
    ) -> int:
        """
        Save a parsed contract to the database.
        
        Args:
            original_file: Original file path or identifier
            tokenized_text: Text with PII tokenized
            ai_response: Raw AI response with tokens
            detokenized_response: AI response with tokens replaced
            token_mapping: Mapping of tokens to original values
            
        Returns:
            ID of the saved contract record
            
        Raises:
            Exception: If database operation fails
        """
        logger.info(f"Saving parsed contract: {original_file}")
        
        session = self.get_session()
        try:
            contract = ParsedContract(
                original_file=original_file,
                tokenized_text=tokenized_text,
                ai_response=ai_response,
                detokenized_response=detokenized_response,
                token_mapping=token_mapping
            )
            
            session.add(contract)
            session.commit()
            session.refresh(contract)
            
            contract_id = contract.id
            logger.info(f"Successfully saved contract with ID: {contract_id}")
            
            return contract_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save contract: {e}")
            raise
        finally:
            session.close()
    
    def get_contract_by_id(self, contract_id: int) -> Optional[ParsedContract]:
        """
        Retrieve a contract by its ID.
        
        Args:
            contract_id: Contract ID
            
        Returns:
            ParsedContract instance or None if not found
        """
        logger.info(f"Retrieving contract with ID: {contract_id}")
        
        session = self.get_session()
        try:
            contract = session.query(ParsedContract).filter(ParsedContract.id == contract_id).first()
            
            if contract:
                logger.info(f"Found contract: {contract}")
            else:
                logger.warning(f"Contract not found with ID: {contract_id}")
            
            return contract
            
        except Exception as e:
            logger.error(f"Failed to retrieve contract: {e}")
            raise
        finally:
            session.close()
    
    def get_all_contracts(self, limit: int = 100, offset: int = 0) -> tuple[list[ParsedContract], int]:
        """
        Retrieve all contracts with pagination.
        
        Args:
            limit: Maximum number of contracts to return
            offset: Number of contracts to skip
            
        Returns:
            A tuple containing the list of ParsedContract instances and the total count.
        """
        logger.info(f"Retrieving contracts (limit={limit}, offset={offset})")
        
        session = self.get_session()
        try:
            total = session.query(ParsedContract).count()
            contracts = (
                session.query(ParsedContract)
                .order_by(ParsedContract.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            
            logger.info(f"Retrieved {len(contracts)} of {total} total contracts")
            return contracts, total
            
        except Exception as e:
            logger.error(f"Failed to retrieve contracts: {e}")
            raise
        finally:
            session.close()
    
    def delete_contract(self, contract_id: int) -> bool:
        """
        Delete a contract by its ID.
        
        Args:
            contract_id: Contract ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        logger.info(f"Deleting contract with ID: {contract_id}")
        
        session = self.get_session()
        try:
            contract = session.query(ParsedContract).filter(ParsedContract.id == contract_id).first()
            
            if contract:
                session.delete(contract)
                session.commit()
                logger.info(f"Successfully deleted contract with ID: {contract_id}")
                return True
            else:
                logger.warning(f"Contract not found with ID: {contract_id}")
                return False
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete contract: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            session = self.get_session()
            session.execute("SELECT 1")
            session.close()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False