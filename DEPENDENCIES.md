# Dependencies and upgrades

Versions checked against PyPI, npm and upstream releases on 2026-10-11.
sqlparse 0.6.0 was added and checked against PyPI on 2026-10-17.
All direct Python package pins below are the latest stable, non-yanked releases
on that date. Install them with Python 3.14.

All plugin types share one plugin service. Jobe is the separate execution
service for student code and teacher tests. The table distinguishes where each
dependency is installed or loaded; installation in the plugin service does not
make a library available to student code in Jobe.

| Dependency | Version | Installed / used by |
| --- | --- | --- |
| Python | 3.14.8, Debian Trixie slim | Plugin service |
| Python | 3.14.4, Ubuntu package 3.14.4-1ubuntu0.2 | Jobe: Python/SQL execution and system tooling |
| SQLite | 3.46.1, verified 2026-10-16 | Jobe: Python `sqlite3` module for Python/SQL execution |
| GCC / G++ | 15.2.0, Ubuntu package 15.2.0-16ubuntu1 | Jobe: C/C++ compilation |
| FastAPI | 0.143.0 | Plugin service |
| Uvicorn, standard extras | 0.54.0 | Plugin service |
| Pydantic | 2.14.0 | Plugin service |
| Pillow | 12.3.0 | Plugin service |
| HTTPX2 | 2.13.1 | Plugin service |
| python-multipart | 0.0.32 | Plugin service |
| Jinja2 | 3.1.6 | Plugin service |
| MarkupSafe | 3.0.4 | Plugin service |
| itsdangerous | 2.2.0 | Plugin service |
| Pylint | 4.1.2 | Plugin service: Python linting; also installed in Jobe's Python environment |
| NumPy | 2.5.4 | Plugin service and Jobe: Python library available to student code and teacher tests |
| Markdown | 3.11 | Plugin service |
| Ruff | 0.17.0 | Plugin service: Python formatting, including SQL teacher tests |
| clang-format | 23.1.3 | Plugin service: C/C++ formatting |
| sqlparse | 0.6.0 | Plugin service: SQL formatting |
| tzdata | 2026.5 | Local development on Windows only; Linux images use OS timezone data |
| Catch2 | 3.16.1 | Jobe: C++ teacher tests for C/C++ answers |
| {fmt} | Ubuntu `libfmt-dev` 10.1.1+ds1-4build1, verified 2026-10-31 | Jobe: C++ answers and teacher tests |
| Ace | 1.44.0 | Browser: bundled and served by the plugin service |
| jQuery | 4.0.0 | Browser: official CDN in the standalone development dialog; supplied by the host in LeTTo |

`requirements.txt` is shared by local development and the plugin image.
SQL formatting uses sqlparse in the plugin service, with uppercase keywords,
four-space indentation, and preserved comments and literals. Python tests in the
SQL plugin reuse Ruff. Jobe does not install sqlparse and does not need rebuilding
for this addition. Reinstall requirements or rebuild the plugin image to apply it.
Jobe Python 3.14.4 and GCC/G++ 15.2.0 were rechecked from the built image on
2026-10-31; the dated native package snapshots below remain separate from apt pins.
clang-format comes from its binary wheel, so local and container formatting use
the same version. Ace is bundled under `resources/vendor/ace/1.44.0` and served
locally at `<serviceBase>/static/ace/1.44.0/` by all four plugin scripts. The
standalone dialog loads jQuery from the official jQuery CDN; in LeTTo, jQuery
is supplied by the host application.

Jobe's build and runtime images use Ubuntu 26.04 LTS. Its Python patch version
follows Ubuntu's maintained package rather than Python's newest upstream bugfix
release. Its system Python must be
3.14, checked during the image build. Student submissions use the interpreter
at `/opt/jobe-python/bin/python3`, with NumPy and Pylint selected from the same
requirements file. This virtual environment keeps pip packages separate from
Ubuntu's system packages. The Jobe installer, healthcheck and C/C++ compiler
driver use system Python. Its patch release and other native packages (Apache,
PHP, GCC, Java, Node.js, Octave, Pascal, SQLite and supporting libraries) follow
Ubuntu's repositories, including distribution security fixes; these are not
necessarily the newest upstream versions. Plugin native libraries follow
Debian Trixie. Jobe itself currently tracks its upstream `master` branch through
`JOBE_VERSION`; that is a moving development branch, not a stable release pin.
Its [latest tag, v2.2.2](https://github.com/trampgeek/jobe/tags), predates sandbox
cleanup fixes present in the existing master-based image. This upgrade retains
that branch rather than reverting those fixes to obtain a release tag.

HTTPX2 replaces HTTPX as recommended by the current Starlette test client.
The application keeps the same HTTP client API for registration and readiness
requests. Windows needs the `tzdata` package for `zoneinfo`; Linux images use
the operating system's timezone database.

## Update policy

Jobe installs `libfmt-dev` from Ubuntu for `<fmt/format.h>` and `fmt::format`.
C++ Run and all Catch2 tests link fmt with `-lfmt`, including
C++ teacher tests for C answers. No task-specific flags are required. The image
build compiles and runs a C++17 fmt smoke test. Rebuild and recreate both services
after this addition. On upgrades, check `dpkg-query -W libfmt-dev`, Python and
GCC/G++ in the resulting Jobe image, run the fmt integration tests, and update
this file and the help pages. See the [official fmt documentation](https://fmt.dev/latest/api/).
The rebuilt Jobe image was checked on 2026-10-31: `libfmt-dev`
10.1.1+ds1-4build1, Python 3.14.4 (3.14.4-1ubuntu0.2), and GCC/G++ 15.2.0
(15.2.0-16ubuntu1). These native packages follow Ubuntu updates rather than
exact apt pins.

The teacher-facing [environment help](resources/help/Environment.html) lists
the verified Jobe interpreter, compiler, installed Python libraries and plugin
tools, with documentation links. It is available from both detailed help pages
at `<serviceBase>/static/help/Environment.html`. When upgrading or rebuilding,
verify the deployed versions and update that page and the version summaries in
`resources/help/Python.html` and `resources/help/Cpp.html`. Native versions above
are dated verification snapshots as noted above; they are not apt pins.

Stay on the Python 3.14 minor series and deliberately adopt its newest bugfix
release. An exact Docker tag such as `python:3.14.8-slim-trixie` controls when the
interpreter changes. `python:3.14-slim-trixie` automatically follows bugfix
releases when pulled. Exact tags improve repeatability, but base images and
native package repositories can still change; immutable builds also require
image digests, a transitive dependency lock and package repository snapshots.

Pin direct Python packages to exact versions and update them together after
checking compatibility. pip selects compatible transitive dependencies using
upstream constraints; it does not install prereleases by default. Major updates
need regression checks, especially changes to validation, grading and formatting.

For Windows, create a fresh virtual environment with the installed Python 3.14:

```powershell
py -3.14 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip list --outdated
```

Select `.venv/Scripts/python.exe` as the IDE interpreter. An existing Python
3.12 environment must be recreated to change its interpreter. On Linux, use
`python3.14 -m venv .venv` and `.venv/bin/python` instead.

For future upgrades, verify release metadata at [PyPI](https://pypi.org/),
[Python](https://www.python.org/downloads/),
[Catch2](https://github.com/catchorg/Catch2/releases),
[Ace](https://github.com/ajaxorg/ace/releases), and
[jQuery](https://blog.jquery.com/). Update the pins and this table, build both
images with `--no-push`, and run the repository tests against the rebuilt plugin
and Jobe. Check the development dialogs after browser-library upgrades.
