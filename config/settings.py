# 📁 config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

JARVIS_ENV = os.getenv("JARVIS_ENV", "development")
DEFAULT_MEMORY_FILE = "jarvis_memory.json"
MODULES_PATH = "modules"
VOICE_MODEL_PATH = "/opt/models/vosk"
