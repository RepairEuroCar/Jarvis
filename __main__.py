# -----------------------------
# jarvis/__main__.py
# -----------------------------
import asyncio
import logging
<<<<<<< HEAD
import sys

from .cli import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("jarvis.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
=======

from utils.logger import setup_logging

from .cli import run

setup_logging(level=logging.INFO)
>>>>>>> main

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nJarvis завершил работу.")
