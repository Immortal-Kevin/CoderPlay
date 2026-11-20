# Third-party inventory and license review

v1.0.1 note: this document remains the **source-distribution** inventory. The
new portable binary has a separate actual-component audit in
[PORTABLE_LICENSES.md](PORTABLE_LICENSES.md), original notice texts under
`licenses/portable/`, and a per-file MANIFEST.json inside the ZIP. It uses an
original .NET launcher/stdlib build script, not the rejected cx_Freeze toolchain.

Review date: 2026-11-19 (America/Los_Angeles). Delivery scope: **source only**,
original PNG charts, documentation and explicitly identified license notices.
No interpreter, Tcl/Tk DLL, package wheel, font, data file, installer, bundler
or EXE is redistributed. There are **zero runtime pip dependencies**.

Own source: Apache-2.0, complete text in LICENSE, attribution in NOTICE.
Third-party notices in `licenses/` retain their owners and licenses; they are
not original application code and are not relicensed as Apache-2.0.

## Runtime platform (not bundled)

| Component | Tested fixed version | SPDX | Source and evidence | Redistribution duty if bundled later | Status |
|---|---|---|---|---|---|
| CPython / standard library / Tkinter | 3.14.7, 64-bit, conda-forge environment already installed | Python-2.0 (includes PSF and historical terms) | Actual installed LICENSE_PYTHON.txt copied to licenses/Python-3.14.7.txt; [upstream](https://docs.python.org/3.14/license.html) | Preserve complete applicable notices, document modifications; Python's own license permits commercial closed applications | Verified license; not distributed |
| Tcl | 8.6.13 | TCL | Actual `info patchlevel`; [versioned upstream license](https://github.com/tcltk/tcl/blob/core-8-6-13/license.terms), licenses/Tcl-8.6.13.txt | Preserve copyright and verbatim terms, retain file-specific notices | Verified license; not distributed |
| Tk | 8.6.13 | TCL | Actual `package require Tk`; installed `tk8.6/license.terms` copied to licenses/Tk-8.6.13.txt; [terms](https://www.tcl-lang.org/software/tcltk/license.html) | Preserve copyright and verbatim terms, retain file-specific notices | Verified license; not distributed |
| Windows GDI/User32, system CRT, system fonts | Host Windows installation | OS-provided, not an open-source dependency | Calls only OS drawing APIs; fonts resolved by family name | No OS DLL or font file is copied. Any separate redistribution needs its own review | External platform only |

Python APIs used include csv, cmath, math, random, dataclasses, threading,
queue, json, pathlib, ctypes, struct and zlib. The zlib codec is supplied by
Python, not bundled by this project. This inventory does not assert that every
unrelated package in the user's existing Python/conda environment is compliant.
No such package is imported by the application. An EXE must additionally audit
the exact interpreter, Tcl/Tk patches, zlib (Zlib), libffi (MIT), CRT and every
other actually bundled file and extension. No current EXE claim is made.

## Test dependencies, including all resolved transitive packages

Exact test lock: requirements-dev.txt. Installed distribution license files were
read and copied unchanged into `licenses/development/<name>/`. Metadata alone
was not used as the license determination. Files are hashed in
`licenses/manifest.json`; the offline audit checks notices and fixed versions.
Pytest's extra dev/docs dependencies are not enabled or installed.

| Package | Fixed version | SPDX reviewed | Source | Duty if redistributed | Status |
|---|---|---|---|---|---|
| pytest | 9.0.2 | MIT | [PyPI](https://pypi.org/project/pytest/9.0.2/) | Retain copyright/license | Verified actual LICENSE; test only |
| iniconfig | 2.3.0 | MIT | [PyPI](https://pypi.org/project/iniconfig/2.3.0/) | Retain copyright/license | Verified actual LICENSE; transitive test only |
| packaging | 25.0 | Apache-2.0 OR BSD-2-Clause | [PyPI](https://pypi.org/project/packaging/25.0/) | Choose either license; preserve applicable notices | Verified LICENSE plus both texts; transitive test only |
| pluggy | 1.6.0 | MIT | [PyPI](https://pypi.org/project/pluggy/1.6.0/) | Retain copyright/license | Verified actual LICENSE; transitive test only |
| colorama | 0.4.6 | BSD-3-Clause | [PyPI](https://pypi.org/project/colorama/0.4.6/) | Retain notice/conditions/disclaimer; no endorsement | Verified actual LICENSE.txt; Windows transitive test only |
| Pygments | 2.19.2 | BSD-2-Clause | [PyPI](https://pypi.org/project/Pygments/2.19.2/) | Retain notice/conditions/disclaimer and AUTHORS | Verified actual LICENSE/AUTHORS; transitive test only |

## Bootstrap tool actually used: pip 26.2.1

Pip is MIT; it installs tests and is never imported by the application or
redistributed. Its installed license tree was read, not inferred from pip's
top-level MIT label. Original notices are retained under `licenses/bootstrap/`.
The actual `pip/_vendor/vendor.txt` is preserved as
`licenses/pip-vendor-versions.txt`. No package build backend was used: test
packages were installed as pure-Python wheels. No bundling tool was installed.

All rows below are **verified against pip's actual vendored license files**, and
are bootstrap-only, not runtime or distributed code. Versioned upstream source:
[pip 26.2.1 vendor tree](https://github.com/pypa/pip/tree/26.2.1/src/pip/_vendor).
Individual wheel/package sources are also available under their corresponding
name and version at PyPI. No unlisted optional extras were enabled.

| Vendored component | Fixed version | SPDX | Distribution obligations if reused |
|---|---|---|---|
| CacheControl | 0.14.4 | Apache-2.0 | License/notices, mark changes |
| distlib | 0.4.2 | PSF-2.0 | Complete inherited PSF/Python notices; modification summary |
| distro | 1.9.0 | Apache-2.0 | License/notices, mark changes |
| msgpack | 1.1.2 | Apache-2.0 | License/notices, mark changes |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | Applicable selected license/notices |
| platformdirs | 4.10.0 | MIT | Copyright/license |
| pyproject-hooks | 1.2.0 | MIT | Copyright/license |
| requests | 2.34.2 | Apache-2.0 | License/notices, mark changes |
| certifi CA bundle | 2026.6.17 | MPL-2.0 | File-level MPL terms and source availability for covered files if distributed |
| idna | 3.18 | BSD-3-Clause | Notices/conditions/disclaimer; no endorsement |
| urllib3 | 2.7.0 | MIT | Copyright/license |
| rich | 14.2.0 | MIT | Copyright/license |
| Pygments | 2.20.0 | BSD-2-Clause | Notices/conditions/disclaimer |
| resolvelib | 1.2.1 | ISC | Copyright/permission/disclaimer |
| setuptools (pkg_resources subset) | 70.3.0 | MIT | Copyright/license |
| tomli | 2.4.1 | MIT | Copyright/license |
| tomli-w | 1.2.0 | MIT | Copyright/license |
| truststore | 0.10.4 | MIT | Copyright/license |

The bootstrap CA bundle's MPL is not GPL/LGPL and does not require opening
unrelated proprietary modules. No CA bundle or certifi code is shipped or used
by FFT Playground. Copying its notice for audit does not introduce it as a
runtime dependency. The test installation tool does access PyPI, whereas the
delivered application does not perform networking.

## Outcome and future commercial modules

**PASS for this source distribution:** no GPL, AGPL, LGPL, paid-commercial,
unknown-license or dual-commercial dependency is included. No unresolved
prohibited component. No fee is required to redistribute this source or add
independent proprietary modules while satisfying the existing notices.

This is an artifact-specific engineering inventory, not an approval of arbitrary
future binaries. No third-party code, asset or database was copied into the
runtime. No MobiusEX file is included. Do not silently introduce scientific
binary wheels or a bundler later: audit the actual files and their notices,
including transitive/native components, before any binary delivery. Current
Python/Tcl/Tk platform prerequisites are not a bundled EXE toolchain.
