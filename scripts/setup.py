import subprocess
import sys
from pathlib import Path


def install_dependencies(requirements: str = "requirements.txt") -> None:
    """Install pip dependencies from *requirements* file."""
    if not Path(requirements).is_file():
        raise FileNotFoundError(requirements)
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements], check=True)
