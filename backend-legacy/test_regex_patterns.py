#!/usr/bin/env python3

import re

# Test the current regex patterns
user_prompt = "Check HKD hedge capacity for 25000 on 2025-09-05"

param_extractors = {
    'currency': r'(?i)\b([A-Z]{3})\s+hedge|new\s+([A-Z]{3})\s+hedge|(?:amount|with)\s+\d+\s*([A-Z]{3})|([A-Z]{3})\s+(?:exposure|position|capacity)',
    'amount': r'(?i)(?:amount|with amount|for)\s+([0-9]+(?:\.[0-9]+)?)\s*([kmb]?)\b',
    'entity_id': r'(?i)(?:for|entity)\s+([A-Z]+[0-9]+[A-Z0-9]*)',
    'order_id': r'(?i)(?:order|using order)\s+([A-Z0-9_-]+)',
    'sub_order_id': r'(?i)(?:sub-order|suborder)\s+([A-Z0-9_-]+)',
    'previous_order_id': r'(?i)(?:previous|prev).*?(?:order|ord)[-_]?([0-9A-Z-]+)',
    'nav_type': r'(?i)\b(COI|RE|RE_Reserve)\b',
    'time_period': r'(?i)(\d{4}-\d{2}-\d{2})|(Q[1-4][-\s]?20[0-9]{2})',
    'confidence_level': r'(?i)([0-9]{1,2})%?\s*(?:confidence|conf)',
    'portfolio': r'(?i)(?:portfolio|fund|account)[:=\s]+([A-Z0-9_]+)',
    'hedge_method': r'(?i)\b(COH|MTM|MT|Swap\s+Pt|Fringe)\b'
}

print(f"Testing prompt: {user_prompt}\n")

for param, pattern in param_extractors.items():
    match = re.search(pattern, user_prompt)
    if match:
        print(f"{param}: Found match - {match.groups()}")
        if param == 'currency':
            currency_code = None
            for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                if match.group(i):
                    currency_code = match.group(i)
                    break
            print(f"  -> Extracted currency: {currency_code}")
        elif param == 'amount':
            amount_value = None
            multiplier = ''
            for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                if match.group(i) and match.group(i).replace('.', '').isdigit():
                    amount_value = float(match.group(i))
                    if i + 1 <= match.lastindex and match.group(i + 1):
                        multiplier = match.group(i + 1).upper()
                    break
            print(f"  -> Extracted amount: {amount_value} (multiplier: {multiplier})")
        elif param == 'time_period':
            time_value = None
            for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                if match.group(i):
                    time_value = match.group(i)
                    break
            print(f"  -> Extracted time: {time_value}")
        else:
            print(f"  -> Extracted: {match.group(1)}")
    else:
        print(f"{param}: No match")
    print()