"""AI client for interacting with the xAI Grok API."""

import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .config import settings

logger = logging.getLogger(__name__)


class GrokAPIError(Exception):
    """Custom exception for Grok API errors."""
    pass


class GrokClient:
    """Client for interacting with the xAI Grok API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the Grok client.
        
        Args:
            api_key: xAI API key (defaults to settings)
            base_url: xAI API base URL (defaults to settings)
        """
        self.api_key = api_key or settings.xai_api_key
        self.base_url = base_url or settings.xai_base_url
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        logger.info(f"Initialized Grok client with base URL: {self.base_url}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def analyze_contract(self, tokenized_text: str) -> Dict[str, Any]:
        """
        Analyze a contract using the Grok API.
        
        Args:
            tokenized_text: Contract text with PII tokenized
            
        Returns:
            Parsed JSON response from Grok
            
        Raises:
            GrokAPIError: If the API call fails
        """
        logger.info("Sending contract analysis request to Grok API")
        
        prompt = self._create_analysis_prompt(tokenized_text)
        
        try:
            response = self.client.chat.completions.create(
                model="grok-beta",  # Use the appropriate Grok model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal contract analysis expert. Analyze contracts and provide structured insights in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            logger.info("Successfully received response from Grok API")
            
            # Parse JSON response
            try:
                parsed_response = json.loads(content)
                return parsed_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Return the raw content if JSON parsing fails
                return {
                    "error": "Failed to parse JSON response",
                    "raw_content": content
                }
                
        except Exception as e:
            logger.error(f"Grok API call failed: {str(e)}")
            raise GrokAPIError(f"API call failed: {str(e)}")
    
    def _create_analysis_prompt(self, tokenized_text: str) -> str:
        """
        Create a structured prompt for contract analysis.
        
        Args:
            tokenized_text: Contract text with PII tokenized
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
Please analyze the following contract text and provide a comprehensive analysis in JSON format.

Contract Text:
{tokenized_text}

Please provide your analysis in the following JSON structure:

{{
    "key_dates_and_events": [
        {{
            "date": "specific date or date reference",
            "event": "description of what happens on this date",
            "importance": "high/medium/low",
            "dependencies": ["list of other dates/events this depends on"]
        }}
    ],
    "date_dependencies": [
        {{
            "dependent_event": "event that depends on another",
            "dependency": "what it depends on",
            "relationship": "description of the relationship (e.g., '30 days after effective date')"
        }}
    ],
    "simplified_clauses": [
        {{
            "original_clause": "original complex clause text",
            "simplified": "plain English explanation",
            "key_points": ["list of key points"]
        }}
    ],
    "benefit_analysis": [
        {{
            "clause": "clause or provision",
            "benefits_party": "buyer/seller/both/neutral",
            "explanation": "why this benefits the specified party",
            "risk_level": "high/medium/low"
        }}
    ],
    "contract_summary": {{
        "contract_type": "type of contract",
        "main_parties": ["party 1", "party 2"],
        "primary_purpose": "main purpose of the contract",
        "key_obligations": ["list of main obligations"],
        "termination_conditions": ["conditions under which contract can be terminated"],
        "governing_law": "applicable law/jurisdiction"
    }},
    "risk_assessment": {{
        "high_risk_items": ["items that pose high risk"],
        "medium_risk_items": ["items that pose medium risk"],
        "recommendations": ["recommendations for risk mitigation"]
    }}
}}

Important notes:
1. Preserve any PII tokens (like [PII_NAME_1], [PII_EMAIL_1]) exactly as they appear in the text
2. Be thorough but concise in your analysis
3. Focus on actionable insights
4. Ensure all JSON is properly formatted and valid
"""
        
        return prompt