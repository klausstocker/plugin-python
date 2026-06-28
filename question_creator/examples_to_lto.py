#!/usr/bin/env python3
"""Convert question example folders into a LeTTo ``.lto`` import file.

Each example folder is expected to contain:
- ``answer.py``: reference/student starter code for the Python plugin
- ``test_answer.py``: unittest-based validation code
- ``README.md``: task text shown above the plugin answer field

By default the script scans sibling directories of this file and writes a
single ``examples.lto`` file containing one question per example. If the input
path is itself one example folder, only that folder is converted and the default
output path is ``<foldername>.lto`` next to the folder.
"""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LINTER_CONFIG = "--disable=C0114,C0115,C0116"


@dataclass(frozen=True)
class ExampleQuestion:
    """Source files for one generated LeTTo question."""

    slug: str
    name: str
    readme: str
    indication: str
    validation: str


def cdata(value: str) -> str:
    """Wrap a value in XML CDATA, safely splitting embedded CDATA endings."""

    return "<![CDATA[" + value.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def read_text(path: Path) -> str:
    """Read UTF-8 text with a clear error message for missing files."""

    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required example file is missing: {path}") from exc


def is_example_dir(path: Path) -> bool:
    """Return whether a path is one importable example directory."""

    return (
        path.is_dir()
        and (path / "answer.py").is_file()
        and (path / "test_answer.py").is_file()
    )


def discover_examples(examples_dir: Path) -> list[Path]:
    """Return example directories that contain the required Python files."""

    return sorted(path for path in examples_dir.iterdir() if is_example_dir(path))


def examples_for_input(input_path: Path) -> list[Path]:
    """Return the single example or child examples selected by the input path."""

    if is_example_dir(input_path):
        return [input_path]

    return discover_examples(input_path)


def default_output_for_input(input_path: Path) -> Path:
    """Return the default .lto output path for a single example or collection."""

    if is_example_dir(input_path):
        return input_path.with_suffix(".lto")

    return input_path / "examples.lto"


def load_example(example_dir: Path) -> ExampleQuestion:
    """Load one example directory into an intermediate representation."""

    slug = example_dir.name
    title = slug.replace("_", " ").title()
    return ExampleQuestion(
        slug=slug,
        name=title,
        readme=read_text(example_dir / "README.md"),
        indication=read_text(example_dir / "answer.py"),
        validation=read_text(example_dir / "test_answer.py"),
    )


def markdown_as_question_html(markdown: str) -> str:
    """Render README content conservatively for LeTTo question text.

    The converter intentionally avoids a Markdown dependency; preserving the
    README in a ``pre`` block keeps code snippets and instructions readable in
    the imported question.
    """

    return f"<pre>{html.escape(markdown)}</pre>\n\n<p>[Q0]</p>\n"


def plugin_payload(question: ExampleQuestion, linter_config: str) -> str:
    """Build the Python plugin payload stored in the LeTTo question."""

    config = {
        "indication": question.indication,
        "validation": question.validation,
        "files": {},
        "evalConfig": {"runAtTest": True, "lintAtTest": True},
        "linterConfig": linter_config,
        "linterWeight": 0,
        "datasetVariables": [],
    }
    payload = {
        "validation": question.validation,
        "indication": question.indication,
        "linterConfig": linter_config,
        "linterWeight": 0.5,
        "config": json.dumps(config, ensure_ascii=False),
        "datasetVariables": [],
        "files": {},
        "evalConfig": {"runAtTest": True, "lintAtTest": True},
    }
    return f'[[PI Plugin1 Python "{json.dumps(payload, ensure_ascii=False)}"]]'


def question_xml(question: ExampleQuestion, index: int, linter_config: str) -> str:
    """Create one LeTTo question XML block."""

    base_id = 90000000 + index * 100
    question_text = markdown_as_question_html(question.readme)
    return f"""<question type=\"MoodleClozeCalc\">
   <id>{base_id}</id>
   <idUser>0</idUser>
   <questionType>22</questionType>
   <single>0</single>
   <name>{cdata(question.name)}</name>
   <punkte>1.0</punkte>
   <penalty/>
   <hidden>0</hidden>
   <tag>{cdata('python-example,' + question.slug)}</tag>
   <noAutoCorrect>0</noAutoCorrect>
   <usecase>0</usecase>
   <synchronize>0</synchronize>
   <shuffleAnswers>1</shuffleAnswers>
   <answerNumbering>{cdata('abc')}</answerNumbering>
   <unitGradingType>2</unitGradingType>
   <unitPenalty>0.1</unitPenalty>
   <showUnits>0</showUnits>
   <unitsLeft>0</unitsLeft>
   <maxima/>
   <responseFormat>{cdata('editor')}</responseFormat>
   <responseFieldLines>10</responseFieldLines>
   <attachments>3</attachments>
   <md5/>
   <units/>
   <plugins>{cdata(plugin_payload(question, linter_config))}</plugins>
   <sendToParser>true</sendToParser>
   <preCalc>true</preCalc>
   <streng>false</streng>
   <licenceKey />
   <konstanteMitProzent>true</konstanteMitProzent>
   <useSymbolicMode>false</useSymbolicMode>
   <addDocumentsPossible>false</addDocumentsPossible>
   <info/>
   <randomDataset>false</randomDataset>
   <creationDate></creationDate>
   <lastChange></lastChange>
   <security/>
   <copyright/>
   <onRamp>false</onRamp>
   <jsonMap>{cdata('{}')}</jsonMap>
   <changeLogMap>{cdata('{}')}</changeLogMap>
   <questionCommentMsg/>
   <questionCommentIcon>PROCESSING</questionCommentIcon>
   <text art=\"Questiontext\" id=\"{base_id + 1}\" format=\"\">   <inhalt>{cdata(question_text)}</inhalt>
</text>
   <text art=\"general feedback\" id=\"{base_id + 2}\" format=\"\">   <inhalt/>
</text>
   <subquestion>
      <id>{base_id + 10}</id>
      <grade>1.0</grade>
      <mode>6</mode>
      <name>{cdata('Q0')}</name>
      <maxima/>
      <plugininfo>{cdata('Plugin1:')}</plugininfo>
      <shuffleAnswers>1</shuffleAnswers>
      <schwierigkeit>0</schwierigkeit>
      <answer>
         <id>{base_id + 20}</id>
         <fraction>100.0</fraction>
         <format>{cdata('html')}</format>
         <text/>
         <feedback/>
         <tolerance>{cdata('1%')}</tolerance>
         <correctAnswerFormat>2</correctAnswerFormat>
         <correctAnswerLength>5</correctAnswerLength>
         <maxima/>
         <answer>{cdata('""')}</answer>
         <einheit/>
      </answer>
   </subquestion>
</question>"""


def build_lto(questions: list[ExampleQuestion], linter_config: str) -> str:
    """Build a complete LeTTo XML document."""

    body = "\n".join(
        question_xml(question, index, linter_config)
        for index, question in enumerate(questions, start=1)
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<letto mode="101" databaseinfo="sql">\n{body}\n</letto>\n'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Python example folders into a LeTTo .lto import file.",
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent,
        help=(
            "Example folder or directory containing example subfolders "
            "(default: this script's directory)."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Output .lto path. Defaults to <foldername>.lto next to a single "
            "example folder, or <input_path>/examples.lto for a collection."
        ),
    )
    parser.add_argument(
        "--linter-config",
        default=DEFAULT_LINTER_CONFIG,
        help=f"Pylint options embedded into each question (default: {DEFAULT_LINTER_CONFIG!r}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input_path.resolve()
    if not input_path.is_dir():
        raise SystemExit(f"Input path is not a directory: {input_path}")

    output = args.output or default_output_for_input(input_path)
    questions = [load_example(path) for path in examples_for_input(input_path)]
    if not questions:
        raise SystemExit(f"No example folders found in {input_path}")

    output.write_text(build_lto(questions, args.linter_config), encoding="utf-8")
    print(f"Wrote {len(questions)} question(s) to {output}")


if __name__ == "__main__":
    main()
