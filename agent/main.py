import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from focus_agent.ui import launch

if __name__ == "__main__":
    base = (
        Path(sys.executable).parent
        if getattr(sys, "frozen", False)
        else Path(__file__).parent
    )
    load_dotenv(base / ".env")
    parser = argparse.ArgumentParser(description="Visible Focus Mode companion")
    parser.add_argument(
        "--adapter",
        choices=["mock", "windows"],
        default=os.getenv("FOCUS_ADAPTER", "mock"),
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "FocusMode"),
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Open mock UI with temporary state, then quit safely after 3 seconds",
    )
    args = parser.parse_args()
    if args.smoke_test:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="focus-package-smoke-") as directory:
            launch(directory, "mock", auto_quit_ms=3000)
    else:
        launch(args.data_dir, args.adapter)
