#!/usr/bin/env python3
"""
Test currency extraction from user prompts
"""

import re

def test_currency_extraction():
    """Test the currency extraction regex"""
    
    # This is the updated pattern from prompt_intelligence_engine.py
    currency_pattern = r'(?i)(?:hedge|check|analyze|for)\s+(?:\d+(?:\.\d+)?\s*(?:k|m|b)?\s+)?([A-Z]{3})\b|(?:\d+(?:\.\d+)?\s*)([A-Z]{3})\b(?:\s+(?:currency|exposure|hedge|position))?|(?:about|what)\s+([A-Z]{3})\s+(?:exposure|hedge|position)'
    
    test_prompts = [
        "Would like to check whether I can hedge 150000 CAD 2025-09-04 for Utilisation.",
        "Check HKD hedge capacity for 50000",
        "Analyze USD position for 100000",
        "can we hedge 250000 EUR",
        "What about SGD exposure of 75000"
    ]
    
    print("Testing Currency Extraction Patterns")
    print("=" * 50)
    
    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")
        
        # Test current pattern with multiple groups
        match = re.search(currency_pattern, prompt)
        if match:
            # Handle multiple groups like the updated extraction logic
            currency_code = match.group(1) if match.group(1) else (match.group(2) if match.group(2) else match.group(3))
            if currency_code:
                extracted = currency_code.upper()
                print(f"Extracted: '{extracted}'")
            else:
                print("No currency extracted")
        else:
            print("No currency extracted")
        
        # Test all 3-letter uppercase patterns in the prompt
        all_matches = re.findall(r'\b[A-Z]{3}\b', prompt)
        print(f"All 3-letter patterns: {all_matches}")

if __name__ == "__main__":
    test_currency_extraction()