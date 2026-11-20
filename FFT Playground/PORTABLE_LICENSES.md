# Portable runtime license audit — v1.0.2

This document covers the **actual folder ZIP**, separately from the source-only
v1.0 audit. Own C# launcher and Python application: Apache-2.0. No pip bundler
is used. A pre-existing Windows .NET Framework C# compiler builds only our own
launcher; the compiler and .NET assemblies are **not** redistributed. The
Windows .NET Framework4.x runtime is an OS prerequisite. No commercial license
purchase is needed; closed commercial modules are permitted subject to the
notices below. No GPL/AGPL/LGPL tool or runtime code is used in this package.

## Actual components

| Component | Pinned version/source | SPDX or exact terms | Distribution obligation and verification |
|---|---|---|---|
| Original launcher/application |1.0.2, tools/PortableLauncher.cs and project sources |Apache-2.0 |Keep LICENSE/NOTICE; mark changes. Source is included in application/ |
| CPython executable, python314.dll, stdlib and selected .pyd extensions |Official Windows x64 3.14.7; python.org distribution URL recorded in MANIFEST.json |Python-2.0 and incorporated permissive terms |Complete original LICENSE.txt plus Doc/license.rst retained; interpreter core signature checked as Python Software Foundation; every packaged file has a SHA256 |
| Tcl and Tk, embedded script libraries |9.0.4; CPython dependency snapshot tcltk-9.0.4.0 |TCL |Keep verbatim Tcl/Tk copyright, permissions and disclaimers; exact dependency-snapshot notices retained |
| Tcl regular expression implementation |Henry Spencer1998/1999, fixed tcl-9.0.4.0 source snapshot |LicenseRef-Henry-Spencer-1998 |Explicit royalty-free source/binary use permitted for any purpose; exact header notice/disclaimer retained; not GNU regex |
| Tk embedded NanoSVG parser/rasterizer |Fixed tk-9.0.4.1 source snapshot used by CPython3.14.7 |Zlib |Mikko Mononen copyright and both original license headers retained; no origin misrepresentation |
| Tk Windows Xlib compatibility files |Fixed tk-9.0.4.1 source snapshot |TCL |Source-tree Xlib/X11 license.terms retained, in addition to Tk top-level terms |
| Tcl's external LibTomMath |Fixed Tcl9.0.4.0 dependency snapshot |Unlicense |Public-domain dedication/warranty disclaimer retained from exact Tcl source snapshot; no inferred separate version |
| Tcl zlib1.dll |1.3.2, same Tcl dependency snapshot |Zlib |Keep origin/notice; do not misrepresent upstream authorship; exact source-tree license retained |
| CPython's statically incorporated zlib-ng |2.2.4, v3.14.7 PCbuild/get_externals.bat |Zlib |Original notice retained, identify origin; not a GNU library |
| libffi-8.dll |3.4.4 CPython binary dependency |MIT |Copyright/permission/disclaimer retained |
| CPython incorporated algorithms/data |As fixed by CPython v3.14.7 source tree |Multiple permissive terms, detailed in upstream Doc/license.rst |Entire upstream incorporated-software license document included, covering Python's builtin components; no optional readline/GPL binary is included |
| vcruntime140.dll and statically linked Microsoft runtime portions |Exact bytes from official CPython3.14.7 Windows distribution; DLL product version recorded with audit |LicenseRef-Microsoft-Distributable-Code |Complete Windows binary conditions retained in CPython-Windows-3.14.7.txt. Preserve notices; do not imply Microsoft endorsement; Windows use only; no malicious/deceptive/unlawful distribution. Applies to Microsoft code only |
| System DLLs, Universal CRT, GDI/User32, .NET Framework, system fonts |Installed Windows platform |OS-provided terms; not copied |Not distributed; no font files or OS DLLs are bundled |

Native file list: python.exe, python314.dll, vcruntime140.dll,
_ctypes.pyd, _tkinter.pyd, _queue.pyd, _socket.pyd, select.pyd,
unicodedata.pyd, libffi-8.dll, libtommath.dll, tcl90.dll, tcl9tk90.dll,
zlib1.dll, plus the original FFT Playground.exe launcher. The `_socket` module
is needed by Python's logging.handlers import; no network connection is made.
No OpenSSL, SQLite, scientific DLL, GNU runtime, pip, site-packages or package
installer is bundled. The stdlib ZIP excludes tests, idlelib, ensurepip, venv,
_pyrepl and turtledemo; no bundled wheels or third-party assets are copied.

`MANIFEST.json` records every packaged file's size/SHA256 and all normal/delayed
PE imports. Build fails if a dependency is neither bundled nor an explicitly
listed Windows system/API-set library. `python314._pth` isolates the runtime
from installed interpreters, registry paths, working directory and site packages.
Source distribution licenses under licenses/portable/ include exact origin URLs.
All14 third-party native files have valid Authenticode signatures (13 Python
Software Foundation,1 Microsoft Windows), recorded in native-signatures.json.
The original launcher is unsigned. All544 copied stdlib sources were also
compared against the official CPython v3.14.7 Git blob IDs after newline
normalization; every file matched. stdlib-upstream.json records that verification,
and both build and ZIP audit recheck it offline. The package is sourced from
the verified installed official distribution; the upstream archive checksum
in MANIFEST is provenance metadata, not a claim that a separate archive was
fully downloaded and hash-verified during this repair.

Rejected option: cx_Freeze8.5.2 → freeze-core0.8.1 → cabarchive0.2.5 (LGPL).
Only wheels were downloaded for review under ignored build/; none was installed
or used for this build and none is distributed. PyInstaller was not used either.

No guarantee is made for a differently assembled future executable. Re-run the
file-level audit after any runtime, tool, component or application change.
