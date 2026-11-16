# Ace editor

The plugin serves Ace 1.44.0 locally from this directory. Docker copies these
files into the image; no browser or runtime download is required.

Source: https://registry.npmjs.org/ace-builds/-/ace-builds-1.44.0.tgz
Upstream: https://github.com/ajaxorg/ace-builds
License: BSD, included in `1.44.0/LICENSE`.

The files come unchanged from the package's `src-min-noconflict` directory:
`ace.js`, `mode-python.js`, `mode-c_cpp.js`, `theme-monokai.js`, `theme-chrome.js` and
`ext-searchbox.js`. Python and C/C++ modes do not use Ace workers.

To upgrade, copy these files and the package's `LICENSE` into a new version
directory, update the version in all four plugin scripts and DEPENDENCIES.md,
then rebuild the plugin image. Include additional modes, extensions or workers
here if future editor features need them.

All Python, C/C++ and SQL editors use LeTTo's `lettoDunkel()` from the bundled
`resources/plugins/plugintools.js`. Dark and soft-dark select Monokai and green
output on black; default, soft-light and high-contrast select Chrome and black
output on white. `lettoOnUmgebung()` updates existing editors and outputs on
design changes. Shared integration lives in `resources/plugins/editor-theme.js`
and unregisters removed roots. Light is the default if LeTTo or the theme helper
scripts are unavailable or the environment helpers fail.
