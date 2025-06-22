# -----------------------------
# jarvis/cli.py
# -----------------------------
import asyncio
import atexit
import os
import platform
<<<<<<< HEAD
import sys

from .core.main import Jarvis
=======
import readline

from command_dispatcher import CommandDispatcher, InvalidCommandError
from jarvis.core.main import Jarvis
from utils.logger import get_logger

logger = get_logger().getChild("CLI")
>>>>>>> main



async def run():
    jarvis = Jarvis()
    dispatcher = CommandDispatcher(jarvis)
    await jarvis.initialize()

    # -----------------------------
    # Setup readline history and completion
    # -----------------------------
    commands: list[str] = []
    for mod, actions in dispatcher._handlers.items():
        for act in actions:
            commands.append(f"{mod} {act}" if act is not None else mod)

    def completer(text: str, state: int) -> str | None:
        matches = [c for c in commands if c.startswith(text)]
        return matches[state] if state < len(matches) else None

    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")

    histfile = os.path.expanduser("~/.jarvis_cli_history")
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass
    atexit.register(lambda: readline.write_history_file(histfile))
    print(f"Jarvis CLI (Python {platform.python_version()})")
    print(f"User: {jarvis.user_name}\n")
    print("Type 'help' for commands. Type 'exit' to quit.\n")

    while True:
        try:
            prompt = f"[{jarvis.user_name}]> "
            line = await asyncio.to_thread(input, prompt)
            text = line.strip()
            if not text:
                continue

            chain = [t.strip() for t in text.split("&&") if t.strip()]
            if len(chain) > 1:
                results = await dispatcher.dispatch_chain(chain)
                exit_seen = False
                for cmd_text, result in zip(chain, results):
                    if result is CommandDispatcher.EXIT:
                        print("Exiting Jarvis...")
                        exit_seen = True
                        break
                    if result is not None:
                        print(result)
                        continue
                    parsed = await jarvis.nlu.process(cmd_text)
                    cmd = parsed.get("intent")
                    handler_tuple = jarvis.commands.get(cmd)
                    if handler_tuple:
                        cmd_info, handler = handler_tuple
                        args = parsed.get("entities", {}).get("raw_args", "")
                        output = (
                            await handler(args) if cmd_info.is_async else handler(args)
                        )
                        print(output)
                    else:
                        print(f"Unknown command: {cmd}")
                if exit_seen:
                    break
                continue

            try:
                result = await dispatcher.dispatch(text)
            except InvalidCommandError as e:
                print(f"Invalid command: {e}")
                continue
            if result is CommandDispatcher.EXIT:
                print("Exiting Jarvis...")
                break
            if result is not None:
                print(result)
                continue

            parsed = await jarvis.nlu.process(text)
            cmd = parsed.get("intent")
            handler_tuple = jarvis.commands.get(cmd)
            if handler_tuple:
                cmd_info, handler = handler_tuple
<<<<<<< HEAD
                args = result.get("entities", {}).get("raw_args", "")
                output = (
                    await handler(args) if cmd_info.is_async else handler(args)
                )
=======
                args = parsed.get("entities", {}).get("raw_args", "")
                output = await handler(args) if cmd_info.is_async else handler(args)
>>>>>>> main
                print(output)
            else:
                print(f"Unknown command: {cmd}")

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            logger.error(f"Ошибка в CLI: {e}")
            print(f"Error: {e}")
