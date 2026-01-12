$ErrorActionPreference = "Stop"

if (-Not (Test-Path .venv)) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pytest

pyinstaller .\WhereDidMyTimeGo.spec

if (-Not (Test-Path dist\WhereDidMyTimeGo.exe)) {
    Write-Error "Build failed: dist\\WhereDidMyTimeGo.exe not found."
}
