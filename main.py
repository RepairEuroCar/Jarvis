import asyncio
import logging

from cli import run
from utils.logger import setup_logging

setup_logging(level=logging.INFO)


async def main() -> None:
    """Entry point that starts the command line interface."""
    await run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarvis завершил работу.")
