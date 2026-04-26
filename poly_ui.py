#!/usr/bin/env python3
import sys
import subprocess

def main():
    cmd = [sys.executable, "main.py", "--provider", "openai"] + sys.argv[1:]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
