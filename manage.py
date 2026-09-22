#!/usr/bin/env python
"""Django's command-line utility for the ATLAS project."""

import os
import subprocess
import sys
from pathlib import Path


def use_project_virtualenv():
    """Re-run management commands with the project's virtual environment."""
    project_root = Path(__file__).resolve().parent
    executable_name = "python.exe" if os.name == "nt" else "python"
    executable_directory = "Scripts" if os.name == "nt" else "bin"
    project_python = project_root / ".venv" / executable_directory / executable_name

    if not project_python.is_file():
        return

    try:
        already_using_project_python = (
            Path(sys.executable).resolve() == project_python.resolve()
        )
    except OSError:
        already_using_project_python = False

    if not already_using_project_python:
        completed = subprocess.run(
            [str(project_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            check=False,
        )
        raise SystemExit(completed.returncode)


def main():
    use_project_virtualenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atlas.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Run `python -m pip install -r requirements.txt`."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
