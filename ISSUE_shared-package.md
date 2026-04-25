# Issue: Package `shared/` as an installable Python package

## Context
The current service imports runtime helpers from the repository-local `shared/` directory (e.g. `shared.check`, `shared.lint`, `shared.jobe_wrapper`).

To make this robust and reusable, we should package `shared/` as an installable Python package instead of relying on source-copy layout inside the container.

## Problem
- Runtime currently depends on `COPY shared ./shared` in `Dockerfile`.
- Imports can break if folder layout changes or if code is reused in another execution context.
- Versioning and reuse of shared logic across services is harder without package metadata.

## Proposal
Create a proper Python package for `shared` and install it in the image/build pipeline.

### Suggested implementation approach
1. Add package metadata (`pyproject.toml`) for a package name like `letto-pluginpython-shared`.
2. Keep module namespace import-compatible (`shared.*`) or migrate to a new namespace with a documented transition.
3. Install package during image build (e.g. `pip install .` or `pip install -e .` for dev).
4. Update CI/tests to run in an installed-package context.
5. Add a short migration note to `README.md`.

## Acceptance criteria
- `shared` functionality is available via package installation, not only via Docker `COPY`.
- App starts successfully with package-installed shared modules.
- Existing endpoints `/run`, `/lint`, `/check` continue to work.
- Local tests and container build pass with the new packaging approach.
- Documentation explains local/dev install path.

## Out of scope
- Functional rewrites of `shared.check`, `shared.lint`, or `shared.jobe_wrapper` logic.
- Changes to external Jobe service behavior.

## Priority
Medium (technical debt / maintainability).
