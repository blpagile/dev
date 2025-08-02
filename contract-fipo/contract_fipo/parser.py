"""Document parsing functionality for PDF and text files."""

import re
import logging
from pathlib import Path
from typing import Union, Optional
import pdfplumber

logger = logging.getLogger(__name__)


class DocumentParser:
    """Handles parsing of PDF and text documents."""
    
    def __init__(self):
        """Initialize the document parser."""
        pass
    
    def parse_file(self, file_path: Union[str, Path]) -> str:
        """
        Parse a file and extract text content.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Extracted and cleaned text content
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file type is not supported
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            return self._parse_pdf(file_path)
        elif file_extension in ['.txt', '.text']:
            return self._parse_text_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def parse_text(self, text: str) -> str:
        """
        Parse and clean raw text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        return self._clean_text(text)
    
    def _parse_pdf(self, file_path: Path) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        logger.info(f"Parsing PDF file: {file_path}")
        
        text_content = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.debug(f"Processing page {page_num}")
                    page_text = page.extract_text()
                    
                    if page_text:
                        text_content.append(page_text)
                    else:
                        logger.warning(f"No text found on page {page_num}")
            
            full_text = "\n\n".join(text_content)
            logger.info(f"Successfully extracted text from {len(pdf.pages)} pages")
            
            return self._clean_text(full_text)
            
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise
    
    def _parse_text_file(self, file_path: Path) -> str:
        """
        Read content from a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            File content
        """
        logger.info(f"Reading text file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            logger.info(f"Successfully read text file: {len(content)} characters")
            return self._clean_text(content)
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    content = file.read()
                logger.info(f"Successfully read text file with latin-1 encoding")
                return self._clean_text(content)
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        logger.debug(f"Cleaned text: {len(text)} characters")
        return text