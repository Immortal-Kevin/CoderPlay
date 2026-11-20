# v1.0 verification record

Date: 2026-11-19, America/Los_Angeles. Windows host, Python 3.14.7,
Tcl/Tk 8.6.13. All results below were actually executed; desktop-window
automation limitations are stated separately. Test runner: pytest 9.0.2.

## Final executed suite

`python -m pytest -q` → **61 passed, 0 failed, 0 skipped**, 4.56 seconds.
`python tools/license_audit.py --development` → PASS, 34 license/notice/version
files hash-verified, all six installed test dependencies match the fixed lock,
zero runtime pip packages, zero prohibited/unknown distributed components.
`python -m pip check` → No broken requirements found.

| Required acceptance | Status | Executed evidence |
|---|---|---|
| 1. 50 Hz, amplitude1 | PASS | N=4096, Fs=4096: 50.0 Hz, Hann 0.9999999999999992, Rectangular 0.9999999999999991; errors <1e-12%, required ≤2% |
| 2. 50+100 Hz | PASS | Automatic peak selection detects both; amplitudes1 and0.7 checked against known model |
| 3. Windows and leakage | PASS | Both windows calibrated at aligned bins; nonaligned50.5 Hz Hann far-sidelobe energy <1% of Rectangular in60–199 Hz; independent DFT comparisons |
| 4. Periodic impacts | PASS | Time-domain ring-down maxima spacing agrees with1/12 s within2 samples; dominant envelope peak12 Hz; raw/envelope spectra differ |
| 5. AM sidebands | PASS | Carrier1000 Hz amplitude1;985/1015 Hz amplitude0.3; envelope15 Hz amplitude0.6; envelope DC1 when enabled, near0 for this stationary example when removed |
| 6. Fs/T/RPM update | PASS | Numeric and actual Tk update tests: Fs3000, T1.1, RPM1200 → N3300, Δf3000/3300, plot arrays and status update |
| 7. Invalid Nyquist/filter parameters | PASS | 16 parameter rejection cases, plus actual GUI update callback rejects invalid band without replacing last result |
| 8. CSV/PNG and data preservation | PASS | Raw exact round-trip, swapped Chinese/English columns, FFT/Envelope metadata, empty/invalid/large file rejection, no overwrites; actual Windows GDI three-canvas PNG dimensions checked |
| 9. Numerical and real Windows GUI tests | PASS | Independent O(N²) DFT oracle for6 lengths incl. prime/odd; real Tk roots and actual event dispatch, not mock GUI/rendering; window start/update tested |
| 10.1366×768 layout | PASS | Actual Tk geometry1366×768; all visible buttons checked inside client bounds, three plot canvases≥120 px height and>800 px wide; all parameter tabs also checked at1320×680 to leave room for the1366×768 desktop title bar/taskbar |
| 11. License audit | PASS | Source-only distribution, full notice files, direct/transitive test tools and bootstrap vendor tree reviewed; no binary packager or runtime pip dependency |
| 12. Offline and shutdown | PASS | Separate Python `-S` process (site packages disabled), socket creation prohibited, actual GUI exports and closes normally; separate close-during-compute process exits within10 s, application creates no subprocesses |

Actual Tk interaction tests dispatch MouseWheel, ButtonPress, drag and Motion
events, confirm independent zoom/pan/coordinate output, invoke Start/Pause/Stop
and Reset buttons, import a real temporary CSV through the UI callback and
verify its bytes remain unchanged. File dialog selection is supplied by the
test; native file-picker manual operation is not claimed.

`python tools/gui_smoke.py docs/charts.png` → actual GUI geometry1366×768,
N8192, Δf0.5, original chart PNG exported, normal WM_DELETE_WINDOW callback.
The exported PNG was visually inspected. An anchor-alignment issue found in
the first export was fixed before the final artifact. Maximum arbitrary-length
record benchmark N32767 completed in1.192 seconds on this host. This is a local
measurement, not a performance guarantee; computation runs in a daemon thread.

During development, an intermediate test edit misplaced some test statements;
that was fixed. Repeatedly creating/destroying separate Tk interpreters also
hit one host Tcl initialization error; GUI tests now share the single real Tk
window and reset parameters between cases, matching normal application use.
The final suite above passed after both fixes. No previous failures are hidden
as final passes without a subsequent successful execution.

## NOT TESTED / limitations (three additional manual/platform checks)

1. External Windows desktop automation/manual file-picker and physical mouse
   walkthrough: NOT TESTED. The installed Computer Use helper failed binding
   the returned window twice with `window id ... no longer belongs to ...;
   current owner is ...` (both owner strings were identical). No success is
   claimed for that helper. Real in-process Tk event interaction tests above
   did run. The separately launched demo was cleaned up after helper failure;
   normal shutdown evidence comes from the successful subprocess smoke tests.
2. Windows10 and Python3.11/3.12/3.13 version matrix: NOT TESTED. The available
   host/runtime was used; source deliberately uses Python3.11-compatible APIs.
3. Multiple physical DPI settings / mixed-DPI monitors: NOT TESTED. DPI-aware
   initialization and resizable layout are implemented; only this host and
  1366×768 Tk geometry were exercised.

EXE packaging is outside this source delivery; no packager selected or bundled.
No EXE or bundled-runtime compliance result is asserted. Periodic frequency-domain
filter edges and non-bin-centred amplitude limitations are documented in README.
