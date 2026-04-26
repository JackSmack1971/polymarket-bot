import re

def test_clamping():
    # Mocking the logic from AIService.generate_analysis
    def get_clamped_content(content, prev_p, psi):
        price_match = re.search(r'\$([0-9,]+)', content)
        if not price_match: return content
        
        new_p = float(price_match.group(1).replace(',', ''))
        cap = 800 if psi < 0.02 else 1500 if psi < 0.10 else float('inf')
        
        if abs(new_p - prev_p) > cap:
            clamped_p = prev_p + (cap if new_p > prev_p else -cap)
            # Find the exact string to replace
            target = f"${int(new_p):,}"
            replacement = f"${int(clamped_p):,}"
            content = content.replace(target, replacement)
            content += f" [Clamped: PSI={psi:.3f}]"
        return content

    print("Running Price Clamping Tests...")
    
    # PSI < 0.02 (Cap $800)
    c1 = "Implied price: $101,000 - Moon"
    r1 = get_clamped_content(c1, 100000.0, 0.01)
    print(f"Test 1 (PSI 0.01, Move $1000): {r1}")
    assert "$100,800" in r1

    # PSI 0.05 (Cap $1500)
    c2 = "Implied price: $102,000 - Moon"
    r2 = get_clamped_content(c2, 100000.0, 0.05)
    print(f"Test 2 (PSI 0.05, Move $2000): {r2}")
    assert "$101,500" in r2

    # PSI 0.15 (No Cap)
    c3 = "Implied price: $110,000 - Moon"
    r3 = get_clamped_content(c3, 100000.0, 0.15)
    print(f"Test 3 (PSI 0.15, Move $10000): {r3}")
    assert "$110,000" in r3
    assert "[Clamped" not in r3

    print("All Clamping Tests PASSED.")

if __name__ == "__main__":
    test_clamping()
