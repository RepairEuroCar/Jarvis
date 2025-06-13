import asyncio

from jarvis.core.main import Jarvis


async def main() -> None:
    """Run Jarvis in autonomous mode with voice input enabled."""
    jarvis = Jarvis()
    await jarvis.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarvis autonomous mode stopped.")
