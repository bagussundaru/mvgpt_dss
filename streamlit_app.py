"""
Root entrypoint for Streamlit Community Cloud.
Dispatches directly to app.streamlit_app.
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.streamlit_app import main

if __name__ == "__main__":
    main()
