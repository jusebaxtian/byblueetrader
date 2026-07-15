"""Values baked into the shipped bot binary (overridable via env vars in dev)."""
import os

LICENSE_BACKEND_URL = os.environ.get("BYBLUE_LICENSE_URL", "https://byblueetrader.vercel.app")
# BYBLUE_LICENSE_API_KEY must be set as an env var at build/run time (not hardcoded here).
# Value must match BOT_API_KEY in the backend's .env / Vercel env vars.
LICENSE_API_KEY = os.environ.get("BYBLUE_LICENSE_API_KEY", "dev-key")

# Local, git-ignored override for production builds: bot_config_local.py is never
# committed (see .gitignore) and only exists on the machine producing the release
# build, so the real BOT_API_KEY never lands in version control.
try:
    from byblue.core.bot_config_local import LICENSE_API_KEY  # noqa: F811
except ImportError:
    pass
