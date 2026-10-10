# Formatting endpoints

The student and teacher Format buttons send source, filename, and the question's
`formatterConfig` to the plugin. Results preserve Ace Undo and save the answer or
configuration. Results are discarded if the source changed while formatting.

- `POST /pluginpython/format`: Ruff 0.17.0 from `requirements.txt`.
- `POST /plugincpp/format`: native clang-format from the plugin Dockerfile.

Both endpoints use the execution token and accept
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
