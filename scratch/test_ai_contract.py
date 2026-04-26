import re
from typing import Optional

def extract_price(text: str) -> Optional[float]:
    # GOLD STANDARD REGEX from GEMINI.md
    match = re.search(r'\$([0-9,]+)', text)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except:
            pass
    return None

test_cases = [
    ("Implied price: $105,250 - Strong momentum detected", 105250.0),
    ("The price is $98,000", 98000.0),
    ("Implied price: $1,200,000 - Moon", 1200000.0),
    ("No price here", None),
    ("Price: 1000", None), # Missing $
]

print("Running AI Contract Regex Tests...")
for text, expected in test_cases:
    result = extract_price(text)
    status = "PASS" if result == expected else f"FAIL (Got {result}, Expected {expected})"
    print(f"Text: {text[:40]:<40} | Result: {str(result):<10} | {status}")
