"""
Main execution module entry point for the animation engine package.
Delegates directly to src.cli.main().
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
