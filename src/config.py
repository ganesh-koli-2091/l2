import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
STANDARDS_FILE = DATA_DIR / "standards" / "java_rest_standards.md"

OUTPUT_DIR.mkdir(exist_ok=True)

PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY", "")
MODEL = "@azure-openai-eus2/gpt-4o-mini"
PORTKEY_BASE_URL = "https://portkeygateway.perficient.com/v1"

MAX_TOOL_RETRIES = 3

FAIL_MODE = os.getenv("FAIL_MODE", "false").lower() == "true"

if not PORTKEY_API_KEY:
    raise EnvironmentError(
        "PORTKEY_API_KEY not set. Copy .env.example to .env and fill in your key."
    )
