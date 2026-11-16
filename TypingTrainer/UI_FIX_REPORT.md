# WPF UI fix verification — 2026-11-05

Scope: UI only, existing project. Core.cs, Storage.cs and TrainingTextBox.cs match the SHA-256 baseline in reports/ui-fix-business-baseline.json. No training algorithm, built-in article, database schema or history logic was changed. Integration tests use isolated temporary databases.

Modified UI: src/App.cs; new original WPF resources/helpers src/UiTheme.xaml, src/UiDialog.cs, src/TrendChart.cs. Extended existing ui-tests/Program.cs; no project or UI framework added.

- Requested defaults: 1280×800 DIP; minimum 900×600. Native SingleBorderWindow / CanResize / PerMonitorV2 retained. On desktops too small at high DPI, initial size is constrained to the monitor work area and centered with a margin; no fixed display-sized window or whole-page scale transform.
- Grid uses Star / Auto / Star around content. The home title and four 320×60 DIP buttons form a vertically and horizontally centered group with 18-DIP button gaps. Operation rows wrap; longer pages scroll. Charts render proportionally to their allocated size without Canvas page coordinates.
- Dark palette: #10141D background, #1A2230 surfaces, #F8FAFC text, #94A3B8 secondary text, #334155 borders, #2563EB buttons, #3B82F6 hover, #1D4ED8 pressed. Input/IME controls, dropdown popups/items, list rows/headers, scrollbars, slider, chart/tooltips and app-owned dialogs are themed. Light theme remains available and saved. Existing installations receive a one-time dark UI preference migration in config/ui-v2.applied, after which explicit light preference remains respected.
- Native caption uses supported Windows DWM dark-caption attributes. Minimize, maximize/restore and close are native functional controls, with native drag, double-click and edge-resize behavior.

## PASS

- Release build / self-contained WPF publish: no warnings/errors.
- Core regression suite: 50 PASS / 0 FAIL.
- Extended WPF UI suite: 25 PASS / 0 FAIL; JSON and PNG evidence in reports/ui-fix/.
- Tests cover requested defaults/minimum, centered home with visible buttons, 1920×1080 layout rendering, 100/125/150/200% offscreen rendering, all page palettes, dropdown items, light preference persistence, app modal confirmation, navigation, existing training flow regression, and maximize content staying within work area.
- Real published app started on current machine. Computer-use verified native minimize, restore from minimized state, maximize/restore icon changing, title-bar double-click maximize/restore, native close, and Settings navigation.
- Actual current display reported by Windows: 3120×2080 at 250% DPI (240 DPI); logical desktop 1248×832, working area 1248×784. Initial fit measured 1224×760 at Left=12, Top=12 DIP. This real-host case is separate from requested synthetic DPI renders.

## NOT VERIFIED / limits

- Physical 1920×1080 display and actual Windows 100/125/150/200% DPI combinations, including multi-monitor transitions. No system display settings were changed. Offscreen renders are not physical DPI validation.
- Windows-owned OpenFileDialog/OpenFolderDialog use the Windows-selected system appearance; their dark appearance cannot be guaranteed when the OS uses a light theme. App-owned error/confirmation dialogs use the selected app theme.
- Native title drag and edge resize rely on standard Windows chrome; they are not claimed as individually exercised by the smoke script.

Desktop shortcut continues to target artifacts/portable/TypingTrainer.exe, which is updated by publishing the existing project.
