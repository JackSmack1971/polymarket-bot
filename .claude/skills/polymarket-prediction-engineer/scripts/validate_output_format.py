#!/usr/bin/env python3
"""
validate_output_format.py
Validates that an AI response string conforms to the required Polymarket
prediction terminal output format.

Exit codes:
  0 = PASS
  1 = FAIL (format violation)

Usage:
  python scripts/validate_output_format.py "Implied price: $119,250 - some insight"
  python scripts/validate_output_format.py --file responses.txt
"""

import re
import sys

# The canonical regex used by extract_ai_price() in poly_ui.py / poly_or.py
PRICE_REGEX = re.compile(r'\$([0-9,]+)')

# Full format regex: "Implied price: $NNN,NNN - [insight]"
FORMAT_REGEX = re.compile(
    r'^Implied price: \$[0-9]{2,3},[0-9]{3}'  # price: $XXX,XXX or $XX,XXX
    r' - '                                      # separator
    r'.{1,100}$'                                # insight: 1-100 chars
)

MAX_INSIGHT_CHARS = 100
PRICE_LINE_PREFIX = "Implied price:"


def validate(text: str) -> tuple[bool, list[str]]:
    """
    Returns (passed: bool, errors: list[str])
    """
    errors = []
    text = text.strip()

    # Rule 1: Single line only
    if '\n' in text:
        errors.append("FAIL [multi-line]: Response must be a single line.")
        return False, errors

    # Rule 2: Starts with correct prefix
    if not text.startswith(PRICE_LINE_PREFIX):
        errors.append(
            f"FAIL [prefix]: Must start with '{PRICE_LINE_PREFIX}', "
            f"got: '{text[:40]}...'"
        )

    # Rule 3: Contains parseable price
    price_match = PRICE_REGEX.search(text)
    if not price_match:
        errors.append("FAIL [price-regex]: No '$NNN,NNN' pattern found — "
                      "extract_ai_price() will return None.")
    else:
        price_str = price_match.group(1).replace(',', '')
        try:
            price_val = float(price_str)
            if price_val < 1_000 or price_val > 10_000_000:
                errors.append(
                    f"WARN [price-range]: Price ${price_val:,.0f} outside "
                    "expected BTC range — check for parsing issue."
                )
        except ValueError:
            errors.append(f"FAIL [price-parse]: Could not convert '{price_str}' to float.")

    # Rule 4: Matches full format regex
    if not FORMAT_REGEX.match(text):
        errors.append(
            "FAIL [format-regex]: Does not match "
            "'Implied price: $XXX,XXX - [insight ≤100 chars]'"
        )

    # Rule 5: Insight length
    parts = text.split(' - ', 1)
    if len(parts) == 2:
        insight = parts[1]
        if len(insight) > MAX_INSIGHT_CHARS:
            errors.append(
                f"FAIL [insight-length]: Insight is {len(insight)} chars "
                f"(max {MAX_INSIGHT_CHARS}). Terminal layout will break."
            )
    else:
        errors.append("FAIL [no-separator]: Missing ' - ' separator after price.")

    # Rule 6: No preamble phrases
    preamble_patterns = [
        r'^(the |based on |according to |my |i )',
        r'(therefore|however|in conclusion)',
    ]
    for pat in preamble_patterns:
        if re.search(pat, text, re.IGNORECASE):
            errors.append(
                f"FAIL [preamble]: Preamble/narrative language detected. "
                "Model must output ONLY the price line."
            )
            break

    passed = len(errors) == 0
    return passed, errors


def run_tests():
    """Built-in self-test suite."""
    test_cases = [
        # (input, expected_pass, label)
        ("Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum",
         True, "canonical good output"),
        ("Implied price: $118,900 - Fine ranges pulling down, reach_125k at 0.31",
         True, "fine ranges insight"),
        ("Implied price: $121,400 - Regime shift: <120k bracket dropped 18% this cycle",
         True, "regime change"),
        ("The implied price is $119,250 based on my analysis of the market data.",
         False, "prose preamble"),
        ("Implied price: $119,250 - " + "x" * 101,
         False, "insight too long (101 chars)"),
        ("Implied price: $119,250\nSome extra context",
         False, "multi-line"),
        ("Implied price: $119250 - missing comma in price",
         False, "no comma in price"),
        ("Implied price: $119,250 - A" + "x" * 100,
         False, "insight exactly 101 chars"),
    ]

    print("Running built-in test suite...")
    print("-" * 60)
    passed_count = 0
    for text, expected, label in test_cases:
        ok, errs = validate(text)
        status = "✅" if ok == expected else "❌"
        result = "PASS" if ok else "FAIL"
        print(f"{status} [{label}]: {result}")
        if ok != expected:
            for e in errs:
                print(f"    {e}")
        if ok == expected:
            passed_count += 1

    print("-" * 60)
    print(f"Test results: {passed_count}/{len(test_cases)} correct")
    return passed_count == len(test_cases)


def main():
    args = sys.argv[1:]

    if not args:
        print("Running self-tests (no argument provided)...")
        success = run_tests()
        sys.exit(0 if success else 1)

    if args[0] == "--test":
        success = run_tests()
        sys.exit(0 if success else 1)

    if args[0] == "--file":
        if len(args) < 2:
            print("ERROR: --file requires a filename argument")
            sys.exit(1)
        try:
            with open(args[1]) as f:
                lines = [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            print(f"ERROR: File not found: {args[1]}")
            sys.exit(1)

        all_passed = True
        for i, line in enumerate(lines, 1):
            ok, errs = validate(line)
            status = "✅ PASS" if ok else "❌ FAIL"
            print(f"Line {i}: {status}")
            if not ok:
                all_passed = False
                for e in errs:
                    print(f"  {e}")
        sys.exit(0 if all_passed else 1)

    # Single string validation
    text = " ".join(args)
    ok, errs = validate(text)

    if ok:
        print(f"✅ PASS — format valid")
        price_match = PRICE_REGEX.search(text)
        if price_match:
            price = float(price_match.group(1).replace(',', ''))
            print(f"   Parsed price: ${price:,.0f}")
    else:
        print(f"❌ FAIL")
        for e in errs:
            print(f"   {e}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
