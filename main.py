import asyncio
import logging
import sys

from cli import run


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("jarvis.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


async def main() -> None:
    """Entry point that starts the command line interface."""
    await run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarvis завершил работу.")
