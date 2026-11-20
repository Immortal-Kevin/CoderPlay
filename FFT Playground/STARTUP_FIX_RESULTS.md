# Windows startup repair — v1.0.1

Executed 2026-11-19 (America/Los_Angeles), Windows11 build26300 x64.

## Reproduction and confirmed changes

The reported immediate startup failure was **not reproduced as a process crash**
on this host. Both `py -3 app.py` and the PATH Python could create a Tk window.
The old batch file always preferred `py -3` while the old tests used the project
venv: these resolve to different real installations here (official Python3.14.7
with Tk9.0.4 versus conda-forge Python3.14.7 with Tk8.6.13). The distinction was
measured, not guessed to be the user's crash cause.

A severe **confirmed desktop usability defect** was reproduced at250% DPI:
Tk's point-based fonts scaled to240 DPI but the1320×680 window,332px parameter
column and Canvas axis margins remained unscaled. The real desktop screenshot
showed compressed controls and overlapping plots. The fix scales pixel layout,
wrapping, chart margins/line widths and PNG font rasterization with Tk's DPI,
and caps initial geometry to available screen space. No signal math was changed.

Startup repair also adds a real interpreter/Tk probe, fallback discovery,
15-second probe timeout, precise interpreter/version/traceback diagnostics,
persistent local logs and console pause on failure. Only child-process inherited
Python/Tcl override variables are cleared. The application records startup and
normal shutdown, catches startup exceptions with a native error dialog, and
records Tk callback exceptions with a visible error rather than losing them in
a hidden console. No user/system settings, other projects or references changed.

## Actually observed desktop sessions

- Original `py -3 app.py` remained open; its250% DPI layout defect was visually
  confirmed through the real Windows desktop, not only Tk event tests.
- Repaired source window remained visible across multiple desktop observations.
  Native mouse clicks Start/Pause changed/paused the displayed time window.
- The compiled **FFT Playground.exe** launcher started the package's private
  Python3.14.7/Tk9.0.4 runtime. Its complete GUI was visually observed at250% DPI;
  native desktop Start/Stop clicks changed the waveform and restored the full
  record. It remained open for several minutes while tests/audits ran.
- Original final-EXE desktop screenshot: [docs/desktop.jpg](docs/desktop.jpg).
  All displayed controls/graphs are original project UI and generated data.
- `cmd.exe /c run.bat` also launched the real Tk8.6.13 window, which remained
  visible on the desktop and closed normally with batch exit code0. The final
  EXE's normal desktop close ended both its launcher and child process.
- The native PNG save dialog was opened and canceled on the desktop. Completing
  its file-name entry through the helper was NOT VERIFIED. Separately, the
  actual packaged Tk/GDI renderer exported a240-DPI PNG successfully, which was
  visually inspected. No saved-file success is attributed to the canceled dialog.
- A first pythonw-based launcher candidate hit the existing desktop helper's
  window-binding bug. The delivered launcher uses the bundled console Python
  with `CreateNoWindow=true`; no terminal is shown, and its desktop window was
  successfully targeted and interacted with. The rejected candidate is not
  distributed. This helper bug was not represented as an application crash.

## Regression results

Final suite: **66 passed,0 failed,0 skipped** in9.58 seconds. Includes all61 prior
FFT, envelope, CSV, PNG, GUI and offline/shutdown tests, plus five startup tests:
old-Python rejection, actual exception-to-log/error path, selected/missing
interpreter diagnostics, separate DPI-aware240-DPI layout process, and the
actual `cmd.exe /c run.bat` failure/pause path from a Chinese/space-containing
directory with an intentionally failing Tk probe. The failure-path test is
explicit fault injection, not a claim that the host's installed Tk is broken.

Portable isolation was separately executed with PATH limited to Windows
System32 and deliberately invalid PYTHONHOME/PYTHONPATH. Its `python314._pth`
gave exactly three package-local search paths, with isolated/no-site flags.
AM carrier amplitude1 and Envelope modulation amplitude0.6 passed using the
bundled engine (module path checked), rather than source-tree modules.

## Binary packaging and license decision

The delivered folder ZIP needs no preinstalled Python. Keep the whole extracted
folder; moving only the small launcher EXE is not supported. It uses the OS .NET
Framework4.x runtime (compiler14.8.10001.0 was already installed and is not shipped).
The archive includes only the original launcher/app and a whitelisted official
CPython/Tcl/Tk runtime. Site-packages and scientific/GNU DLLs are excluded.

Actual original Windows Python core signature: Valid, Python Software Foundation.
All14 packaged third-party PE files also had valid signatures from PSF/Microsoft;
all544 stdlib members matched the official v3.14.7 upstream Git blob IDs.
Exact dependency tags/license texts were checked, not just project license labels.
The package's native import audit covers all15 PE files and544 nested stdlib
source members, with retained notices and SHA256 for each. See
[PORTABLE_LICENSES.md](PORTABLE_LICENSES.md). The ZIP audit rejects unlisted
files, unexpected native components, changed notices or unresolved DLL imports.

cx_Freeze was rejected after its Windows dependency chain was found to include
cabarchive (LGPL). Downloaded review wheels are ignored local build material,
not installed, used, committed or distributed. No paid license, PyInstaller,
cx_Freeze, GNU runtime or closed-source disclosure requirement is introduced.

## Remaining limits and directly runnable diagnostics

- The exact user's original instant-close failure cannot be attributed without
  its traceback. This release gives directly runnable `run.bat --diagnose` and
  logs under `%LOCALAPPDATA%\FFT Playground\logs\` for that case.
- Clean Windows10 VM and Python3.11–3.13 matrix: NOT TESTED. Actual desktop
  Windows11, Tk8.6/Tk9.0 and250% DPI are covered; mixed-DPI monitor moves are
  NOT TESTED. The portable runtime was isolated but Python was not uninstalled
  from the host.
- Publisher code signing/SmartScreen reputation: NOT PROVIDED; no certificate
  purchase was made. No claim is made about unsigned-download warning behavior.
