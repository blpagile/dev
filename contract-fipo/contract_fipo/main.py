"""Main entry point for the contract-fipo application."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .parser import DocumentParser
from .pii_handler import PIIHandler
from .ai_client import GrokClient, GrokAPIError
from .db_handler import DatabaseHandler
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    """Main contract analysis orchestrator."""
    
    def __init__(self):
        """Initialize the contract analyzer with all components."""
        self.document_parser = DocumentParser()
        self.pii_handler = PIIHandler()
        self.grok_client = GrokClient()
        self.db_handler = DatabaseHandler()
        
        # Ensure database tables exist
        try:
            self.db_handler.create_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            sys.exit(1)
    
    def analyze_file(self, file_path: str) -> dict:
        """
        Analyze a contract file.
        
        Args:
            file_path: Path to the contract file
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"Starting analysis of file: {file_path}")
        
        try:
            # Step 1: Parse the document
            logger.info("Step 1: Parsing document")
            raw_text = self.document_parser.parse_file(file_path)
            
            if not raw_text.strip():
                raise ValueError("No text content found in the document")
            
            logger.info(f"Extracted {len(raw_text)} characters from document")
            
            # Step 2: Tokenize PII
            logger.info("Step 2: Tokenizing PII")
            tokenized_text, token_mapping = self.pii_handler.tokenize_text(raw_text)
            
            # Step 3: Analyze with Grok AI
            logger.info("Step 3: Analyzing with Grok AI")
            ai_response = self.grok_client.analyze_contract(tokenized_text)
            
            # Step 4: Detokenize the response
            logger.info("Step 4: Detokenizing AI response")
            detokenized_response = self._detokenize_response(ai_response, token_mapping)
            
            # Step 5: Save to database
            logger.info("Step 5: Saving to database")
            contract_id = self.db_handler.save_parsed_contract(
                original_file=file_path,
                tokenized_text=tokenized_text,
                ai_response=ai_response,
                detokenized_response=detokenized_response,
                token_mapping=token_mapping
            )
            
            logger.info(f"Analysis completed successfully. Contract ID: {contract_id}")
            
            return {
                "success": True,
                "contract_id": contract_id,
                "analysis": detokenized_response,
                "pii_entities_found": len(token_mapping)
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_text(self, text: str, source_identifier: str = "direct_input") -> dict:
        """
        Analyze contract text directly.
        
        Args:
            text: Contract text content
            source_identifier: Identifier for the text source
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"Starting analysis of text input: {source_identifier}")
        
        try:
            # Step 1: Clean the text
            logger.info("Step 1: Cleaning text")
            cleaned_text = self.document_parser.parse_text(text)
            
            if not cleaned_text.strip():
                raise ValueError("No text content provided")
            
            # Step 2: Tokenize PII
            logger.info("Step 2: Tokenizing PII")
            tokenized_text, token_mapping = self.pii_handler.tokenize_text(cleaned_text)
            
            # Step 3: Analyze with Grok AI
            logger.info("Step 3: Analyzing with Grok AI")
            ai_response = self.grok_client.analyze_contract(tokenized_text)
            
            # Step 4: Detokenize the response
            logger.info("Step 4: Detokenizing AI response")
            detokenized_response = self._detokenize_response(ai_response, token_mapping)
            
            # Step 5: Save to database
            logger.info("Step 5: Saving to database")
            contract_id = self.db_handler.save_parsed_contract(
                original_file=source_identifier,
                tokenized_text=tokenized_text,
                ai_response=ai_response,
                detokenized_response=detokenized_response,
                token_mapping=token_mapping
            )
            
            logger.info(f"Analysis completed successfully. Contract ID: {contract_id}")
            
            return {
                "success": True,
                "contract_id": contract_id,
                "analysis": detokenized_response,
                "pii_entities_found": len(token_mapping)
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _detokenize_response(self, response: dict, token_mapping: dict) -> dict:
        """
        Detokenize the AI response by replacing tokens with original values.
        
        Args:
            response: AI response containing tokens
            token_mapping: Mapping of tokens to original values
            
        Returns:
            Detokenized response
        """
        import json
        
        # Convert response to JSON string, detokenize, then parse back
        response_str = json.dumps(response)
        detokenized_str = self.pii_handler.detokenize_text(response_str, token_mapping)
        
        try:
            return json.loads(detokenized_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, return the original response
            logger.warning("Failed to parse detokenized response as JSON")
            return response


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Contract FIPO - Analyze contracts with PII protection and AI insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file contract.pdf
  %(prog)s --text "This is a contract between John Doe and Jane Smith..."
  %(prog)s --file contract.txt --output results.json
        """
    )
    
    # Create a main action group that requires at least one argument
    main_group = parser.add_mutually_exclusive_group(required=True)
    
    # Input options (file and text are mutually exclusive within the main group)
    input_subgroup = main_group.add_mutually_exclusive_group()
    input_subgroup.add_argument(
        '--file', '-f',
        type=str,
        help='Path to the contract file (PDF or text)'
    )
    input_subgroup.add_argument(
        '--text', '-t',
        type=str,
        help='Contract text content as a string'
    )
    
    # Database options (part of main group)
    main_group.add_argument(
        '--list-contracts',
        action='store_true',
        help='List all analyzed contracts'
    )
    main_group.add_argument(
        '--get-contract',
        type=int,
        metavar='ID',
        help='Retrieve a specific contract by ID'
    )
    
    # Utility options (part of main group)
    main_group.add_argument(
        '--test-db',
        action='store_true',
        help='Test database connection'
    )
    
    # Output options (not part of main group, can be used with any main option)
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path for results (JSON format)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def main():
    """Main entry point for the CLI application."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        analyzer = ContractAnalyzer()
        
        # Handle utility commands
        if args.test_db:
            if analyzer.db_handler.test_connection():
                print("✅ Database connection successful")
                return 0
            else:
                print("❌ Database connection failed")
                return 1
        
        if args.list_contracts:
            contracts = analyzer.db_handler.get_all_contracts()
            if contracts:
                print(f"Found {len(contracts)} contracts:")
                for contract in contracts:
                    print(f"  ID: {contract.id}, File: {contract.original_file}, Created: {contract.created_at}")
            else:
                print("No contracts found in database")
            return 0
        
        if args.get_contract:
            contract = analyzer.db_handler.get_contract_by_id(args.get_contract)
            if contract:
                print(f"Contract ID: {contract.id}")
                print(f"File: {contract.original_file}")
                print(f"Created: {contract.created_at}")
                print(f"Analysis: {contract.detokenized_response}")
            else:
                print(f"Contract with ID {args.get_contract} not found")
            return 0
        
        # At this point, we know one of the main arguments was provided
        # If it's not a utility command, we need file or text input
        
        # Handle analysis commands
        result = None
        
        if args.file:
            if not Path(args.file).exists():
                print(f"❌ File not found: {args.file}")
                return 1
            result = analyzer.analyze_file(args.file)
        
        elif args.text:
            result = analyzer.analyze_text(args.text)
        
        if result:
            if result["success"]:
                print(f"✅ Analysis completed successfully!")
                print(f"Contract ID: {result['contract_id']}")
                print(f"PII entities found: {result['pii_entities_found']}")
                
                # Save output if requested
                if args.output:
                    import json
                    with open(args.output, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
                    print(f"Results saved to: {args.output}")
                else:
                    # Print summary
                    analysis = result["analysis"]
                    if "contract_summary" in analysis:
                        summary = analysis["contract_summary"]
                        print(f"\nContract Summary:")
                        print(f"  Type: {summary.get('contract_type', 'Unknown')}")
                        print(f"  Parties: {', '.join(summary.get('main_parties', []))}")
                        print(f"  Purpose: {summary.get('primary_purpose', 'Unknown')}")
            else:
                print(f"❌ Analysis failed: {result['error']}")
                return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())