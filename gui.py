import asyncio
import tkinter as tk
from tkinter import filedialog

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

    output = tk.Text(frame, height=20, width=80)
    output.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    entry = tk.Entry(frame, width=60)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(5, 0))

    voice_task: asyncio.Task | None = None
    voice_active = False
    cleanup_task: asyncio.Task | None = None
    history: list[str] = []

    async def run_command(cmd: str) -> None:
        try:
            result = await jarvis.handle_command(cmd)
        except Exception as exc:  # pragma: no cover - GUI feedback only
            output.insert(tk.END, f"Error: {exc}\n")
            history.append(f"Error: {exc}")
        else:
            if result is not None:
                output.insert(tk.END, f"{result}\n")
                history.append(result)
        output.see(tk.END)

    def send_command(event=None) -> None:  # type: ignore[override]
        cmd = entry.get().strip()
        if not cmd:
            return
        output.insert(tk.END, f"> {cmd}\n")
        history.append(cmd)
        entry.delete(0, tk.END)
        asyncio.create_task(run_command(cmd))

    async def voice_loop() -> None:
        nonlocal voice_active, voice_task
        voice_active = True
        while voice_active:
            text = await jarvis.voice_interface.listen()
            if not text:
                continue
            output.insert(tk.END, f"Voice> {text}\n")
            history.append(f"Voice> {text}")
            if jarvis.settings.voice_activation_phrase in text:
                command = text.split(jarvis.settings.voice_activation_phrase, 1)[-1].strip()
                if command:
                    output.insert(tk.END, f"> {command}\n")
                    history.append(command)
                    await run_command(command)
            await asyncio.sleep(0.05)
        voice_task = None

    def toggle_voice() -> None:
        nonlocal voice_task, voice_active
        if voice_task:
            voice_active = False
            voice_button.config(text="Start Voice")
        else:
            voice_task = asyncio.create_task(voice_loop())
            voice_button.config(text="Stop Voice")

    entry.bind("<Return>", send_command)
    btn = tk.Button(frame, text="Send", command=send_command)
    btn.pack(side=tk.RIGHT, padx=(5, 0), pady=(5, 0))

    voice_button = tk.Button(frame, text="Start Voice", command=toggle_voice)
    voice_button.pack(side=tk.RIGHT, padx=(0, 5), pady=(5, 0))

    menu = tk.Menu(root)
    root.config(menu=menu)
    file_menu = tk.Menu(menu, tearoff=False)

    def save_output() -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(output.get("1.0", tk.END))

    def clear_output() -> None:
        output.delete("1.0", tk.END)

    file_menu.add_command(label="Save Output", command=save_output)
    file_menu.add_command(label="Clear Output", command=clear_output)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.destroy)
    menu.add_cascade(label="File", menu=file_menu)

    def show_history() -> None:
        win = tk.Toplevel(root)
        win.title("History")
        box = tk.Text(win, height=20, width=80)
        box.pack(fill=tk.BOTH, expand=True)
        box.insert(tk.END, "\n".join(history))

    view_menu = tk.Menu(menu, tearoff=False)
    view_menu.add_command(label="History", command=show_history)
    menu.add_cascade(label="View", menu=view_menu)

    def open_settings() -> None:
        win = tk.Toplevel(root)
        win.title("Voice Settings")

        tk.Label(win, text="Rate").grid(row=0, column=0, sticky="w")
        rate_var = tk.IntVar(value=jarvis.settings.voice_rate)
        tk.Entry(win, textvariable=rate_var).grid(row=0, column=1)

        tk.Label(win, text="Volume").grid(row=1, column=0, sticky="w")
        volume_var = tk.DoubleVar(value=jarvis.settings.voice_volume)
        tk.Entry(win, textvariable=volume_var).grid(row=1, column=1)

        tk.Label(win, text="Language").grid(row=2, column=0, sticky="w")
        lang_var = tk.StringVar(value=jarvis.settings.recognition_language)
        tk.Entry(win, textvariable=lang_var).grid(row=2, column=1)

        def apply() -> None:
            jarvis.settings.voice_rate = rate_var.get()
            jarvis.settings.voice_volume = volume_var.get()
            jarvis.settings.recognition_language = lang_var.get()
            jarvis.settings.tts_language = lang_var.get()
            if jarvis.voice_interface:
                jarvis.voice_interface.engine.setProperty("rate", rate_var.get())
                jarvis.voice_interface.engine.setProperty("volume", volume_var.get())
                jarvis.voice_interface.update_language()
            win.destroy()

        tk.Button(win, text="Apply", command=apply).grid(row=3, column=0, columnspan=2, pady=5)

    settings_menu = tk.Menu(menu, tearoff=False)
    settings_menu.add_command(label="Voice & Language", command=open_settings)
    settings_menu.add_command(label="Toggle Voice", command=toggle_voice)
    menu.add_cascade(label="Settings", menu=settings_menu)

    commands_menu = tk.Menu(menu, tearoff=False)
    added = set()
    for name, cmd in jarvis.commands.items():
        if cmd.is_alias or name in added:
            continue
        added.add(name)
        commands_menu.add_command(
            label=name,
            command=lambda n=name: asyncio.create_task(run_command(n)),
        )
    menu.add_cascade(label="Commands", menu=commands_menu)

    async def shutdown() -> None:
        nonlocal voice_task, voice_active
        if voice_task:
            voice_active = False
            await voice_task
            voice_task = None
        if jarvis.voice_interface and jarvis.voice_interface.is_active:
            jarvis.voice_interface.stop()
        await jarvis.sensor_manager.stop()
        await jarvis.event_queue.stop()

    def on_close() -> None:
        nonlocal cleanup_task
        if cleanup_task is None:
            cleanup_task = asyncio.create_task(shutdown())
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    async def tk_loop() -> None:
        while True:
            try:
                root.update()
            except tk.TclError:
                break
            await asyncio.sleep(0.05)

    await tk_loop()
    if cleanup_task is not None:
        await cleanup_task


if __name__ == "__main__":
    asyncio.run(main())

