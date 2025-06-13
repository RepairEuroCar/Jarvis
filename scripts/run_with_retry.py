import subprocess
import sys


def check_syntax(path: str) -> None:
    """Compile a Python file to detect syntax errors."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    compile(source, path, "exec")


def main(path: str) -> None:
    """Run a script, prompting to retry on SyntaxError."""
    while True:
        try:
            check_syntax(path)
            subprocess.run([sys.executable, path], check=True)
            break
        except SyntaxError as e:
            print(f"SyntaxError in {path} line {e.lineno}: {e.msg}")
            input("Correct the file and press Enter to retry, or Ctrl+C to abort...")
        except subprocess.CalledProcessError as e:
            print(f"Script {path} exited with return code {e.returncode}")
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <script.py>")
        sys.exit(1)
    main(sys.argv[1])
