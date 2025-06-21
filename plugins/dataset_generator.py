"""Plugin exposing a dataset generation command."""

from jarvis.commands.registry import CommandCategory, CommandInfo
from jarvis.core.main import RegisteredCommand
from modules import dataset_generator


def register(jarvis) -> None:
    async def generate_cmd(event):
        parts = event.text.split()
        if len(parts) < 3:
            return "Usage: dataset_generate <output_dir> <size_gb>"
        out_dir = parts[1]
        try:
            size = float(parts[2])
        except ValueError:
            return "Invalid size"
        await dataset_generator.generate_dataset(out_dir, size)
        return f"Dataset generated in {out_dir}"

    jarvis.commands["dataset_generate"] = RegisteredCommand(
        info=CommandInfo(
            name="dataset_generate",
            description="Generate a synthetic code dataset",
            category=CommandCategory.DEVELOPMENT,
            usage="dataset_generate <output_dir> <size_gb>",
            aliases=["gen_dataset"],
        ),
        handler=generate_cmd,
    )
