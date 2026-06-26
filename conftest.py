import sys
import os

# Add the root directory to Python path for imports like 'from config import ...'
# Note: sitecustomize.py sets up calibre stubs (must be in PYTHONPATH before pytest starts)
sys.path.insert(0, os.path.dirname(__file__))
