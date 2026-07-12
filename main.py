"""
main.py
-------
Root-level entry point for DeskGuard - AI-Powered Workspace Asset
Verification System.

Usage:
    python main.py

This simply delegates to src.app.run(), keeping the root directory
clean while all real logic lives inside the `src` package.
"""

from src.app import run

if __name__ == "__main__":
    run()