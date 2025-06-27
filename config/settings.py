# 📁 config/settings.py
import os

from dotenv import load_dotenv

load_dotenv()

JARVIS_ENV = os.getenv("JARVIS_ENV", "development")
DEFAULT_MEMORY_FILE = "jarvis_memory.json"
MODULES_PATH = "modules"
VOICE_MODEL_PATH = "/opt/models/vosk"

DYNAMIC_SCALER_CHECK_INTERVAL = int(os.getenv("JARVIS_SCALER_INTERVAL", "5"))
DYNAMIC_SCALER_CPU_THRESHOLD = float(os.getenv("JARVIS_SCALER_CPU_THRESHOLD", "80"))
DYNAMIC_SCALER_MEMORY_THRESHOLD = float(os.getenv("JARVIS_SCALER_MEMORY_THRESHOLD", "80"))
