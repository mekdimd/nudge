from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib


def get_version() -> str:
    try:
        return version("nudge")
    except PackageNotFoundError:
        with (Path(__file__).resolve().parents[1] / "pyproject.toml").open("rb") as project:
            return tomllib.load(project)["project"]["version"]
