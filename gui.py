import asyncio
import tkinter as tk

from jarvis.core.main import Jarvis
from utils.logger import setup_logging


async def main() -> None:
    setup_logging()
    jarvis = Jarvis()
    await jarvis.initialize()

    root = tk.Tk()
    root.title("Jarvis GUI")

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)

    output = tk.Text(frame, height=20, width=60)
    output.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    entry = tk.Entry(frame, width=60)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(5, 0))

    async def run_command(cmd: str) -> None:
        try:
            result = await jarvis.handle_command(cmd)
        except Exception as exc:  # pragma: no cover - GUI feedback only
            output.insert(tk.END, f"Error: {exc}\n")
        else:
            if result is not None:
                output.insert(tk.END, f"{result}\n")
        output.see(tk.END)

    def send_command(event=None) -> None:  # type: ignore[override]
        cmd = entry.get().strip()
        if not cmd:
            return
        output.insert(tk.END, f"> {cmd}\n")
        entry.delete(0, tk.END)
        asyncio.create_task(run_command(cmd))

    entry.bind("<Return>", send_command)
    btn = tk.Button(frame, text="Send", command=send_command)
    btn.pack(side=tk.RIGHT, padx=(5, 0), pady=(5, 0))

    async def tk_loop() -> None:
        while True:
            try:
                root.update()
            except tk.TclError:
                break
            await asyncio.sleep(0.05)

    await tk_loop()


if __name__ == "__main__":
    asyncio.run(main())
