# Test report — 2026-11-05

Development status: PARTIAL. This is a working native MVP with explicit DOC/IME/physical verification limits.

## Executed automated tests

- Core/storage/import assertion suite: **50 PASS / 0 FAIL** (tests/Program.cs; process exit code 0).
- WPF integration suite: **16 PASS / 0 FAIL** (ui-tests/Program.cs; temporary isolated database, process exit code 0).
- Build and self-contained win-x64 publish: PASS, no warnings or errors after fixes.
- Microsoft runtime package signature verification: PASS for Microsoft.NETCore.App.Runtime.win-x64 10.0.14 and Microsoft.WindowsDesktop.App.Runtime.win-x64 10.0.14, using `dotnet nuget verify --all`.
- Release packaging tests: recorded separately in reports/package-tests.json after executing archive, installer and uninstall checks.

Core cases include zero/negative time, CPM/WPM, Rune counting, CRLF normalization, edit-distance insertion/deletion/substitution, significant case/whitespace, error retention after corrections, identical character replacement events, composition commit de-duplication at model level, paused clock, wrong-input speed, built-ins, SQLite transactions/persistence/integrity, JSON persistence, duplicate content, deleted-article history, protected built-ins, future schema refusal, migration success and failure rollback, backups, TXT encodings/invalid bytes, DOCX paragraphs/tab/break, oversized/empty/control text, corrupt DOCX and XXE rejection. Legacy DOC rejection is tested; this is not a DOC parsing support claim.

WPF cases include home at 1920×1080 and minimum 900×680, a 144-DPI offscreen render, theme/language regeneration, library/selection/training/results rendering, input changes and target error highlighting, pause locking, auto completion persistence, early end, zero-input exclusion, and native WindowState transitions. Programmatic component edits are test setup only; these are not genuine hardware key/IME tests. Evidence PNGs and JSON are in reports/ui/.

Computer-use smoke: published app launched and exposed a native accessible window; article selection, training entry, keyboard interaction, Ctrl+Enter early settlement and close were exercised. The computer-use screenshot surface returned a blank desktop, so it is not treated as visual layout evidence. Offscreen WPF renders were inspected separately. Do not infer physical IME or screen-DPI success from either test.

## NOT VERIFIED — 6 acceptance groups

1. Real Microsoft Pinyin IME: temporary candidate text, final commit, cancellation, replacement, switching focus during composition and pause/resume during composition. Requires physical input-method testing.
2. Physical display DPI transitions across 100/125/150/200% monitors and complete visual inspection at minimum dimensions. Offscreen render is not this test.
3. Actual keyboard/clipboard/drop/assistive-technology combinations and long-text scroll/caret interaction. Code paths and component tests do not prove every Windows input pathway.
4. Physically disconnected/network-disabled machine: code contains no application network calls, but OS networking was not disabled for testing.
5. Cross-computer Windows 11 x64 Intel hardware deployment; no second-computer test was performed.
6. Full interactive installer/uninstaller UX and SmartScreen behavior. Local silent install/uninstall and extraction checks do not replace those user-facing checks.

## Manual acceptance steps

- Open portable app on Windows 11; maximize/minimize/restore, resize to minimum, then move between monitors at each DPI. Inspect all pages and full-length text wrapping.
- Toggle Chinese/English and both themes; restart and confirm persistence; adjust blue and brightness and inspect text/button/read-only field contrast.
- Start an English article: enter a wrong letter, backspace, select and replace, insert in the middle, tab and newline. Attempt Ctrl+V, Shift+Insert, context-menu paste, drag/drop and UIA Value.SetValue. Verify error marker and caret/scroll behavior.
- With Microsoft Pinyin, type a multi-syllable composition without confirming. Verify no formal character count or timer advance, then commit and check exact event count. Cancel, backspace inside composition, replace a selection, pause mid-composition, switch focus/window, resume, and repeat. Treat discrepancies as release blockers for IME acceptance.
- Pause after formal text for at least 10 seconds and confirm frozen time/input; resume. Complete an article with errors and check automatic settlement. End another early, then exit a zero-input session and inspect history filtering, ordering, deltas and chart tooltips.
- Import UTF-8/UTF-16/GB18030 and a multi-paragraph DOCX; inspect exact whitespace in preview. Verify duplicate, corrupt, empty and >4000-character rejection. DOC must show unsupported explanation.
- Move data to a fresh local directory, restart and check article/result/config integrity. Try nonempty and unwritable destinations, verify source and original location pointer stay safe. Clear history using both confirmations and inspect retained backups.
- Disconnect the computer from the network, run portable and installed versions, train/import/settle/restart, and confirm no SDK or network prompt is needed.
- Run installer interactively, launch from Start menu, uninstall from Windows settings, and confirm data survives. Repeat on a second Windows 11 Intel computer.


