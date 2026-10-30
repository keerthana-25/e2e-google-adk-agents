"""Model names. Override them in .env if needed."""

import os

from dotenv import load_dotenv

load_dotenv()

# fast model for formatting / small tasks, advanced model for research + synthesis
FAST_MODEL = os.getenv("GEN_FAST_MODEL", "gemini-2.5-flash")
ADVANCED_MODEL = os.getenv("GEN_ADVANCED_MODEL", "gemini-2.5-pro")
