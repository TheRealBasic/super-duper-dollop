# Where Did My Time Go?

A local-first Windows 11 desktop app that tracks your foreground app usage, categorizes sessions, and provides daily dashboards and reports.

## Requirements
- Windows 11
- Python 3.11+

## Setup & Run (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m where_did_my_time_go
```

## Permissions
No special permissions are required. The app reads the foreground window and idle time using standard Windows APIs and stores data locally.

## Build EXE (single file)
```powershell
.\build.ps1
```
The output will be placed at `dist/WhereDidMyTimeGo.exe`.

## Run Tests
```powershell
pytest
```

## Sanity Test (2 minutes)
1. Launch the app and keep it running in the tray.
2. Alt-tab between two apps for ~30 seconds each.
3. Return to the app and confirm the dashboard shows time spent on those apps and a session list in Reports.
4. Stop input for longer than the idle threshold and confirm Idle time increases.

## Troubleshooting (PyInstaller / PySide6)
- **Qt platform plugin missing**: Ensure the build uses the provided `WhereDidMyTimeGo.spec`. This bundles the required Qt plugins. Re-run `build.ps1` after deleting the `build/` folder.
- **Antivirus false positives**: Some antivirus tools flag new unsigned executables. Add an exception for `dist/WhereDidMyTimeGo.exe` if needed.
- **Onefile temp extraction**: PyInstaller extracts to a temp folder on each launch. This is normal and expected.

## Notes
- Data is stored locally at `%APPDATA%\WhereDidMyTimeGo\data.db`.
- Provide your own `assets/icon.ico` if you want a custom icon (optional).
- No telemetry or network calls are made.
