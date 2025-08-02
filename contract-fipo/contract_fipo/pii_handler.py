"""PII detection and tokenization functionality."""

import re
import logging
from typing import Dict, List, Tuple, Optional
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

logger = logging.getLogger(__name__)


class PIIHandler:
    """Handles PII detection, tokenization, and detokenization."""
    
    def __init__(self):
        """Initialize the PII handler with Presidio engines."""
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self.use_presidio = True
            logger.info("Initialized PII handler with Presidio")
        except Exception as e:
            logger.warning(f"Failed to initialize Presidio: {e}. Falling back to regex-based detection.")
            self.use_presidio = False
        
        # Token mapping: token -> original value
        self.token_mapping: Dict[str, str] = {}
        self.token_counters: Dict[str, int] = {}
    
    def tokenize_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Detect PII in text and replace with tokens.
        
        Args:
            text: Input text containing potential PII
            
        Returns:
            Tuple of (tokenized_text, token_mapping)
        """
        logger.info("Starting PII tokenization")
        
        # Clear previous mappings
        self.token_mapping.clear()
        self.token_counters.clear()
        
        if self.use_presidio:
            tokenized_text = self._tokenize_with_presidio(text)
        else:
            tokenized_text = self._tokenize_with_regex(text)
        
        logger.info(f"Tokenized {len(self.token_mapping)} PII entities")
        return tokenized_text, self.token_mapping.copy()
    
    def detokenize_text(self, tokenized_text: str, token_mapping: Dict[str, str]) -> str:
        """
        Replace tokens with original PII values.
        
        Args:
            tokenized_text: Text containing PII tokens
            token_mapping: Mapping of tokens to original values
            
        Returns:
            Text with tokens replaced by original PII values
        """
        logger.info("Starting PII detokenization")
        
        detokenized_text = tokenized_text
        
        for token, original_value in token_mapping.items():
            detokenized_text = detokenized_text.replace(token, original_value)
        
        logger.info(f"Detokenized {len(token_mapping)} PII entities")
        return detokenized_text
    
    def _tokenize_with_presidio(self, text: str) -> str:
        """
        Use Presidio to detect and tokenize PII.
        
        Args:
            text: Input text
            
        Returns:
            Tokenized text
        """
        try:
            # Analyze text for PII
            results = self.analyzer.analyze(
                text=text,
                language='en',
                entities=[
                    'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'CREDIT_CARD',
                    'US_SSN', 'US_DRIVER_LICENSE', 'DATE_TIME', 'LOCATION',
                    'IP_ADDRESS', 'URL', 'US_BANK_NUMBER', 'IBAN_CODE'
                ]
            )
            
            # Sort results by start position in reverse order to avoid index shifting
            results.sort(key=lambda x: x.start, reverse=True)
            
            tokenized_text = text
            
            for result in results:
                original_value = text[result.start:result.end]
                entity_type = result.entity_type
                
                # Generate unique token
                token = self._generate_token(entity_type, original_value)
                
                # Replace in text
                tokenized_text = (
                    tokenized_text[:result.start] + 
                    token + 
                    tokenized_text[result.end:]
                )
            
            return tokenized_text
            
        except Exception as e:
            logger.error(f"Error in Presidio tokenization: {e}")
            # Fallback to regex
            return self._tokenize_with_regex(text)
    
    def _tokenize_with_regex(self, text: str) -> str:
        """
        Use regex patterns to detect and tokenize common PII.
        
        Args:
            text: Input text
            
        Returns:
            Tokenized text
        """
        tokenized_text = text
        
        # Define regex patterns for common PII
        patterns = [
            # Email addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),
            # Phone numbers (various formats)
            (r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', 'PHONE'),
            # Social Security Numbers
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            # Credit Card Numbers (basic pattern)
            (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', 'CREDIT_CARD'),
            # IP Addresses
            (r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', 'IP_ADDRESS'),
            # URLs
            (r'https?://[^\s]+', 'URL'),
            # Names (simple pattern - capitalized words)
            (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 'PERSON'),
        ]
        
        for pattern, entity_type in patterns:
            matches = list(re.finditer(pattern, tokenized_text))
            
            # Process matches in reverse order to avoid index shifting
            for match in reversed(matches):
                original_value = match.group()
                token = self._generate_token(entity_type, original_value)
                
                tokenized_text = (
                    tokenized_text[:match.start()] + 
                    token + 
                    tokenized_text[match.end():]
                )
        
        return tokenized_text
    
    def _generate_token(self, entity_type: str, original_value: str) -> str:
        """
        Generate a unique token for a PII entity.
        
        Args:
            entity_type: Type of PII entity
            original_value: Original PII value
            
        Returns:
            Unique token string
        """
        # Increment counter for this entity type
        if entity_type not in self.token_counters:
            self.token_counters[entity_type] = 0
        
        self.token_counters[entity_type] += 1
        counter = self.token_counters[entity_type]
        
        # Create token
        token = f"[PII_{entity_type}_{counter}]"
        
        # Store mapping
        self.token_mapping[token] = original_value
        
        logger.debug(f"Generated token {token} for {entity_type}")
        return token