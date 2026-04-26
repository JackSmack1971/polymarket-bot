#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path

def extract_keywords(skill_content):
    """Extract technical keywords like regexes, constants, and function names."""
    keywords = set()
    # Find regex patterns (simplified)
    keywords.update(re.findall(r'r\'(.*?)\'', skill_content))
    # Find potential constants/function names (TitleCase or snake_case in backticks)
    keywords.update(re.findall(r'`([a-zA-Z0-9_]{3,})`', skill_content))
    # Find Event IDs (5-digit numbers)
    keywords.update(re.findall(r'\b\d{5}\b', skill_content))
    return keywords

def run_grep(keyword):
    """Search for a keyword in the codebase using native Python."""
    matches = 0
    try:
        # Walk through the current directory
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith(('.py', '.md', '.ts', '.js', '.json', '.txt')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            if keyword in f.read():
                                matches += 1
                    except (UnicodeDecodeError, PermissionError):
                        continue
        return f"FOUND ({matches} matches)" if matches > 0 else "MISSING"
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python discover_alignment.py <path_to_skill.md>")
        sys.exit(1)

    skill_path = Path(sys.argv[1])
    if not skill_path.exists():
        print(f"Error: {skill_path} not found.")
        sys.exit(1)

    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"--- Discovering Alignment for {skill_path.name} ---")
    keywords = extract_keywords(content)
    
    if not keywords:
        print("No technical keywords found in skill.")
        return

    print(f"Extracted {len(keywords)} keywords. Grepping codebase...")
    
    results = {}
    for kw in sorted(keywords):
        status = run_grep(kw)
        results[kw] = status
        print(f"  {kw:20} -> {status}")

    print("\n--- Summary ---")
    missing = [k for k, v in results.items() if v == "MISSING"]
    if missing:
        print(f"WARNING: {len(missing)} terms are documented but not found in code:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("SUCCESS: All documented technical terms found in codebase.")

if __name__ == "__main__":
    main()
