#!/usr/bin/env python
"""
Simple test runner that sets up PYTHONPATH and runs pytest.
This ensures sitecustomize.py is found and can set up calibre stubs.
"""
import os
import sys
import subprocess

# Set PYTHONPATH to include the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
python_path = os.environ.get('PYTHONPATH', '')
if python_path:
    python_path = f"{current_dir}{os.pathsep}{python_path}"
else:
    python_path = current_dir

env = os.environ.copy()
env['PYTHONPATH'] = python_path

# Run pytest
result = subprocess.run([sys.executable, '-m', 'pytest'] + sys.argv[1:], env=env)
sys.exit(result.returncode)
