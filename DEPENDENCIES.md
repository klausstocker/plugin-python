# Dependencies and upgrades

Versions checked against PyPI, npm and upstream releases on 2026-10-11.
All direct Python package pins below are the latest stable, non-yanked releases
on that date. Install them with Python 3.14.

| Dependency | Version |
| --- | --- |
| Python (plugin image) | 3.14.8, Debian Trixie slim |
| Python (Jobe image) | 3.14.4, Ubuntu package 3.14.4-1ubuntu0.2 |
| SQLite library (Jobe Python) | 3.46.1, verified in the running Jobe container on 2026-10-16 |
| GCC / G++ (Jobe image) | 15.2.0, Ubuntu package 15.2.0-16ubuntu1 |
| FastAPI | 0.143.0 |
| Uvicorn, standard extras | 0.54.0 |
| Pydantic | 2.14.0 |
| Pillow | 12.3.0 |
| HTTPX2 | 2.13.1 |
| python-multipart | 0.0.32 |
| Jinja2 | 3.1.6 |
| MarkupSafe | 3.0.4 |
| itsdangerous | 2.2.0 |
| Pylint | 4.1.2 |
| NumPy | 2.5.4 |
| Markdown | 3.11 |
| Ruff | 0.17.0 |
| clang-format | 23.1.3 |
| tzdata, Windows only | 2026.5 |
| Catch2 | 3.16.1 |
| Ace | 1.44.0 |
| jQuery, standalone development dialog | 4.0.0 |

`requirements.txt` is shared by local development and the plugin image.
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

The teacher-facing [environment help](resources/help/Environment.html) lists
the verified Jobe interpreter, compiler, installed Python libraries and plugin
tools, with documentation links. It is available from both detailed help pages
at `<serviceBase>/static/help/Environment.html`. When upgrading or rebuilding,
verify the deployed versions and update that page and the version summaries in
`resources/help/Python.html` and `resources/help/Cpp.html`. Native versions above
were read from the running Jobe container on 2026-10-11; they are not apt pins.

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
