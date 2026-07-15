"""Values baked into the shipped bot binary (overridable via env vars in dev)."""
import os

LICENSE_BACKEND_URL = os.environ.get("BYBLUE_LICENSE_URL", "https://license.byblue.example.com")
LICENSE_API_KEY = os.environ.get("BYBLUE_LICENSE_API_KEY", "dev-key")
