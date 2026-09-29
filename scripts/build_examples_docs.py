"""Render the short examples guide with inline solutions."""

import argparse
from pathlib import Path
import sys

import markdown

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.question_examples import EXAMPLE_NAMES


def build(output: Path) -> None:
    guide = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
    for name in EXAMPLE_NAMES:
        solution = (ROOT / "examples" / name / "answer.py").read_text(encoding="utf-8")
        guide = guide.replace(
            f"[Possible solution]({name}/answer.py)",
            "**Possible solution**\n\n```python\n" + solution.rstrip() + "\n```",
        )
    body = markdown.markdown(guide, extensions=["fenced_code"])
    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Python plugin examples</title>
<style>
body { max-width: 960px; margin: 2rem auto; padding: 0 1rem;
       font-family: system-ui, sans-serif; line-height: 1.6; color: #202124; }
pre { padding: 1rem; background: #f3f5f7; overflow-x: auto; line-height: 1.4; }
code { font-family: ui-monospace, monospace; }
h2 { margin-top: 2rem; border-top: 1px solid #ddd; padding-top: 1rem; }
a { color: #1455a0; }
</style>
</head>
<body>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page + body + "\n</body>\n</html>\n",
                      encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "resources/plugins/Python/examples.html")
    build(parser.parse_args().output)
