import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app  # noqa: E402

# Vercel's Python runtime detects this ASGI `app` automatically.
