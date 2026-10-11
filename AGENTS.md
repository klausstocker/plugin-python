# Repository instructions

## Dependency changes

Whenever changing dependencies, runtime or compiler versions, Docker base images,
or bundled tools/libraries (including `requirements.txt`, either Dockerfile,
Catch2, Ace, or jQuery), remind the user to update the help and version
documentation. Include this reminder in the final response and state whether
the relevant documentation was updated or what remains to be verified.

Update the relevant documentation as part of the dependency change:

- `DEPENDENCIES.md`: versions, runtime details, and upgrade instructions.
- `resources/help/Environment.html`: exact verified runtime/compiler versions,
  installed libraries, tools, and official documentation links, grouped by
  Python and C/C++.
- `resources/help/Python.html` and `resources/help/Cpp.html`: affected version
  summaries and configuration guidance. Keep the environment section at the end.
- `resources/formatting/README.md` and `README.md`: affected tool/runtime details.

Verify Jobe Python and GCC/G++ versions from the built or running Jobe image;
do not infer exact native package versions from a Docker base tag. Date verified
version snapshots. If verification is unavailable, clearly identify the pending
check instead of presenting an assumed version as verified.
