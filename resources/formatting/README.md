# Formatting endpoints

Teacher-facing documentation and official tool links are in the shared
[environment help](../help/Environment.html), linked from all three plugin help pages.

The student and teacher Format buttons send source, filename, and the question's
`formatterConfig` to the plugin. Results preserve Ace Undo and save the answer or
configuration. Results are discarded if the source changed while formatting.

- `POST /pluginpython/format`: Ruff 0.17.0 from `requirements.txt`.
- `POST /plugincpp/format`: clang-format 23.1.3, packaged as a binary wheel in `requirements.txt`.
- `POST /pluginsql/format`: sqlparse 0.6.0 for `main.sql` and `preparation.sql`,
  existing Ruff 0.17.0 for `main.py` (Python unit tests).

All endpoints use the execution token and accept
`{code, filename, questionConfigDto: {formatterConfig}}`, returning
`{code, output, timings}`. Errors return an explanatory `output` without replacing
the source. Tools use stdin and a five-second timeout and never execute code.
Only a small shared JavaScript client is downloaded, without a WASM runtime.

The Configuration tab stores `formatterConfig` with each question. Python
supports Ruff TOML (`line-length`, `indent-width`, `target-version`, `preview`, and
`[format]`). It does not read external configs or change Python lint/scoring
settings. C/C++ supports self-contained clang-format YAML. Empty settings use:

```toml
line-length = 88
indent-width = 4
[format]
quote-style = "double"
```

```yaml
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
SortIncludes: Never
AllowShortFunctionsOnASingleLine: None
```

SQL uses fixed defaults: uppercase keywords and four-space reindentation, keeping
comments and string literals. It accepts unfinished SQL without validating or
executing it. The teacher's Format button follows the active tab; students use
Format Code. Python tests use Ruff defaults. SQL questions need no formatter
configuration fields. The same shared client preserves Undo, saves changes, and
discards stale responses. SQL uses the plugin's interpreter in a subprocess with
the same five-second timeout and 128 KiB request limit.

After adding sqlparse, rebuild only the plugin image or reinstall requirements
for local development. Jobe's Python/GCC versions were rechecked from the built
image on 2026-10-17; SQL formatting does not add packages to Jobe.

C/C++ also stores additional `compilerFlags`, e.g. `-O2 -Wextra -DNUMBER=42`.
Flags apply to run, compile, unit tests, and grading, extending defaults C17/C++17,
`-Wall -Werror`. Later flags can override defaults, e.g. `-std=c++20` or
`-Wno-error`. Supported options include standards, optimization, debug info,
warnings, definitions/undefinitions, relative include directories (`-Iinclude`),
`-pthread`, `-pipe`, pedantic checks, and common code-generation switches.
Shell syntax, tool plugins, output paths, response files, and absolute/parent
include paths are rejected. Use attached forms `-DNUMBER=42` and `-Iinclude`.

Catch2 uses those flags too; C standard flags do not replace the C++17 harness
standard for C answers. Test-object cache keys include effective flags.

Rebuild plugin and Jobe images to apply the formatter/compiler changes. For local
development, `RUFF_BIN` and `CLANG_FORMAT_BIN` override executable paths.
Run unit and Jobe integration tests with `py -m unittest discover -s tests -v`
using the normal project Jobe at `localhost:4000` and the normal plugin at
`http://localhost:8209` (override its base URL with `PLUGIN_TEST_SERVER`). No
special test image, headless browser, or local formatter installation is needed.
Ruff and clang-format integration tests call the plugin's endpoints; endpoint
and configuration unit tests use mocks.
`tests.test_sql_formatting` checks real local sqlparse/Ruff output and SQLite
behavior. Install requirements first.
