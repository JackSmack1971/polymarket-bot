#!/usr/bin/env python3
"""
validate_event.py — Zero-dependency Polymarket event structure validator.
Usage: python scripts/validate_event.py <event_id>

Exit codes:
  0 = All checks passed
  1 = Some checks failed (event usable with caveats)
  2 = Critical failure (event unusable)
"""

import sys
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

CHECKS = []
FAILURES = []
CRITICALS = []


def check(name, condition, critical=False):
    """Record a check result."""
    status = "PASS" if condition else "FAIL"
    CHECKS.append((name, status))
    if not condition:
        if critical:
            CRITICALS.append(name)
        else:
            FAILURES.append(name)
    return condition


def http_get(url, timeout=10):
    req = Request(url, headers={"User-Agent": "poly-validator/1.0"})
    with urlopen(req, timeout=timeout) as r:
        data = r.read()
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        s = data.decode("utf-8").strip()
        try:
            return float(s)
        except Exception:
            return None


def validate_event(event_id):
    print(f"\n=== Validating Event {event_id} ===\n")

    # --- CHECK 1: Event fetchable ---
    ev = None
    try:
        ev = http_get(f"{GAMMA_BASE}/events/{event_id}")
    except (URLError, HTTPError) as e:
        check("Event reachable via Gamma API", False, critical=True)
        _print_results()
        return 2

    check("Event reachable via Gamma API", ev is not None, critical=True)
    if not ev:
        _print_results()
        return 2

    # --- CHECK 2: Has markets ---
    has_markets = isinstance(ev, dict) and "markets" in ev and len(ev["markets"]) > 0
    check("Event has markets array", has_markets, critical=True)
    if not has_markets:
        _print_results()
        return 2

    # --- CHECK 3: At least one Yes/No pair ---
    valid_markets = []
    for m in ev["markets"]:
        try:
            tokens = json.loads(m.get("clobTokenIds", "[]"))
            outcomes = json.loads(m.get("outcomes", "[]"))
            prices = json.loads(m.get("outcomePrices", "[]"))
            if len(tokens) == 2 and len(prices) == 2 and outcomes == ["Yes", "No"]:
                valid_markets.append({
                    "question": m.get("question", ""),
                    "yes_token": tokens[0],
                    "no_token": tokens[1],
                    "yes_price": float(prices[0]),
                    "no_price": float(prices[1]),
                    "closed": m.get("closed", False),
                    "resolved": m.get("resolved", False),
                })
        except Exception:
            pass

    check("At least one valid Yes/No market", len(valid_markets) > 0, critical=True)
    if not valid_markets:
        _print_results()
        return 2

    print(f"  Found {len(valid_markets)} valid Yes/No markets:")
    for vm in valid_markets:
        status = " [RESOLVED]" if vm["resolved"] else (" [CLOSED]" if vm["closed"] else "")
        print(f"    [{vm['yes_price']:.3f} / {vm['no_price']:.3f}] {vm['question'][:70]}{status}")

    # --- CHECK 4: Resolved market detection ---
    resolved_count = sum(1 for m in valid_markets if m["resolved"])
    active_count = len(valid_markets) - resolved_count
    check("Has active (unresolved) markets", active_count > 0)
    if resolved_count > 0:
        print(f"\n  WARNING: {resolved_count} resolved market(s) detected — add skip filters.")

    # --- CHECK 5: Price sanity ---
    price_sane = all(
        0.0 <= m["yes_price"] <= 1.0 and 0.0 <= m["no_price"] <= 1.0
        for m in valid_markets
    )
    check("All prices in [0.0, 1.0] range", price_sane)

    # --- CHECK 6: Probability sum per market (arbitrage check) ---
    arb_ok = all(abs((m["yes_price"] + m["no_price"]) - 1.0) < 0.10 for m in valid_markets)
    check("Per-market probability sums within 10% of 1.0", arb_ok)

    # --- CHECK 7: CLOB live price check on first Yes token ---
    first_yes_token = valid_markets[0]["yes_token"]
    clob_price = None
    try:
        j = http_get(f"{CLOB_BASE}/price?token_id={first_yes_token}&side=buy", timeout=5)
        if isinstance(j, dict):
            clob_price = float(j.get("price", 0))
        elif isinstance(j, (int, float)):
            clob_price = float(j)
    except Exception:
        pass

    check("CLOB live price reachable for first Yes token", clob_price is not None)
    if clob_price is not None:
        print(f"\n  CLOB live Yes price for '{valid_markets[0]['question'][:50]}...': {clob_price:.4f}")
        check("CLOB price in valid range [0.0, 1.0]", 0.0 <= clob_price <= 1.0)

    # --- CHECK 8: Bracket pattern detection ---
    questions = [m["question"].lower() for m in valid_markets]
    has_less_than = any("less than" in q for q in questions)
    has_between = any("between" in q for q in questions)
    has_greater = any("greater than" in q for q in questions)
    has_reach_dip = any(("reach" in q or "dip" in q) for q in questions)

    bracket_type = "unknown"
    if has_between and not has_reach_dip:
        bracket_type = "range_brackets"
    elif has_reach_dip:
        bracket_type = "reach_dip"
    elif has_less_than or has_greater:
        bracket_type = "boundary"

    print(f"\n  Detected bracket type: {bracket_type}")
    check("Bracket type identified", bracket_type != "unknown")

    # --- CHECK 9: Dip $120k resolved market skip (event 37057 specific) ---
    if int(event_id) == 37057:
        dip_120_present = any("dip to $120k" in q or "dip to $120k" in m["question"].lower()
                              for m in valid_markets)
        dip_120_resolved = any(
            ("dip to $120k" in m["question"].lower() or "dip to $120k" in m["question"].lower())
            and m["resolved"]
            for m in valid_markets
        )
        if dip_120_present:
            check("Dip $120k market present AND resolved (expected)", dip_120_resolved)
            print("  INFO: 'dip to $120k' market present — ensure skip filter is active in code.")

    # --- Summary ---
    print()
    _print_results()

    if CRITICALS:
        return 2
    if FAILURES:
        return 1
    return 0


def _print_results():
    print("─" * 50)
    print("VALIDATION RESULTS:")
    for name, status in CHECKS:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} [{status}] {name}")
    print(f"\n  Total: {len(CHECKS)} checks | "
          f"Passed: {len(CHECKS) - len(FAILURES) - len(CRITICALS)} | "
          f"Failed: {len(FAILURES)} | Critical: {len(CRITICALS)}")
    if not FAILURES and not CRITICALS:
        print("\n  ✅ Event is VALID — safe to integrate.")
    elif CRITICALS:
        print("\n  ❌ CRITICAL failures — event CANNOT be integrated.")
    else:
        print("\n  ⚠️  Non-critical failures — review before integrating.")
    print("─" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_event.py <event_id>")
        print("Example: python scripts/validate_event.py 37049")
        sys.exit(2)

    event_id = sys.argv[1]
    exit_code = validate_event(event_id)
    if exit_code == 2:
        sys.exit(2)   # Critical failure
    elif exit_code == 1:
        sys.exit(1)   # Non-critical failures
    else:
        sys.exit(0)   # All checks passed
