"""
Root conftest — ensures the backend/ directory is on sys.path so both the
`app` and `eval` packages import cleanly regardless of how pytest is invoked.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
