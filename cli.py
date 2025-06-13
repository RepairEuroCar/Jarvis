# -----------------------------
# jarvis/cli.py
# -----------------------------
import asyncio
import logging
import platform
import sys

from jarvis.core.main import Jarvis

logger = logging.getLogger("Jarvis.CLI")


async def run():
    jarvis = Jarvis()
    await jarvis.initialize()
    print(f"Jarvis CLI (Python {platform.python_version()})")
    print(f"User: {jarvis.user_name}\n")
    print("Type 'help' for commands. Type 'exit' to quit.\n")

    while True:
        try:
            prompt = f"[{jarvis.user_name}]> "
            sys.stdout.write(prompt)
            sys.stdout.flush()
            line = await asyncio.to_thread(sys.stdin.readline)
            text = line.strip()
            if not text:
                continue
            if text.lower() in ["exit", "quit"]:
                print("Exiting Jarvis...")
                break

            result = await jarvis.nlu.process(text)
            cmd = result.get("intent")
            handler_tuple = jarvis.commands.get(cmd)
            if handler_tuple:
                cmd_info, handler = handler_tuple
                args = result.get("entities", {}).get("raw_args", "")
                output = await handler(args) if cmd_info.is_async else handler(args)
                print(output)
            else:
                print(f"Unknown command: {cmd}")

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            logger.error(f"Ошибка в CLI: {e}")
            print(f"Error: {e}")
