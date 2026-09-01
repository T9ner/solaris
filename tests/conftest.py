"""Pytest configuration ensuring workspace root is on sys.path."""

import pathlib
import sys

root_dir = str(pathlib.Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
