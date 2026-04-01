"""Entry point: ``compliance-ui`` launches the Streamlit app."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    from streamlit.web.cli import main as st_main

    app_path = str(Path(__file__).with_name("app.py"))
    sys.argv = ["streamlit", "run", app_path, "--server.headless=true"]
    st_main()


if __name__ == "__main__":
    main()
