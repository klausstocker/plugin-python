"""Render the examples guide and current source files into one resource page."""

import argparse
from html import escape
from pathlib import Path
import sys

import markdown

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.question_examples import EXAMPLE_NAMES


def build(output: Path) -> None:
    guide = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
    body = markdown.markdown(guide, extensions=["fenced_code", "tables", "toc"])
    sources = ["<h2>Templates, checkers, and reference solutions</h2>"]
    for index, name in enumerate(EXAMPLE_NAMES, 1):
        directory = ROOT / "examples" / name
        sources.append(f'<section id="source-{name}"><h3>{index}. {escape(name)}</h3>')
        for filename, label in [
            ("template.py", "Student template (indication)"),
            ("test_answer.py", "Teacher checker (validation)"),
            ("names.txt", "Supplied text fixture"),
            ("answer.py", "Reference solution"),
        ]:
            path = directory / filename
            if not path.exists():
                if filename == "names.txt":
                    continue
                raise FileNotFoundError(path)
            code = escape(path.read_text(encoding="utf-8"))
            sources.append(
                f"<details><summary>{label}: {filename}</summary>"
                f"<pre><code>{code}</code></pre></details>"
            )
        sources.append("</section>")
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
summary { cursor: pointer; padding: .5rem 0; font-weight: 600; }
section { margin: 2rem 0; border-top: 1px solid #ddd; }
a { color: #1455a0; }
</style>
</head>
<body>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page + body + "\n" + "\n".join(sources) + "\n</body>\n</html>\n",
                      encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "resources/plugins/Python/examples.html")
    build(parser.parse_args().output)
