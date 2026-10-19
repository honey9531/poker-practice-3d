# Build and verify PokerPractice.exe on Windows.
#
# Usage (PowerShell or Git Bash; in Git Bash use forward slashes):
#     powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1 [-SkipTests]
#
# Requires Python 3.12 or newer ("py" launcher or "python" on PATH). Produces
# dist\PokerPractice\PokerPractice.exe
# and runs its built-in self-test twice to confirm that history persists.
param([switch]$SkipTests)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Find the full path of a Python 3.12 or newer: the "py" launcher first, then "python" on PATH.
function Find-Python {
    # Probing missing versions writes to stderr; that must not stop the script.
    $ErrorActionPreference = "Continue"
    $probe = "import sys; print(sys.executable if sys.version_info >= (3, 12) else '')"
    foreach ($version in "-3.13", "-3.12", "-3") {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $exe = (& py $version -c $probe 2>$null | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and $exe) { return $exe }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $exe = (& python -c $probe 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe }
    }
    return $null
}

$python = ".\.venv-win\Scripts\python.exe"
if (-not (Test-Path $python)) {
    if (Test-Path .venv-win) { Remove-Item -Recurse -Force .venv-win }  # left over from a failed attempt
    $base = Find-Python
    if (-not $base) {
        throw ("Python 3.12 or newer was not found. Install it from https://www.python.org/downloads/windows/ " +
               "(or: winget install Python.Python.3.12), open a new terminal and run this script again.")
    }
    Write-Host "Creating .venv-win with $base"
    & $base -m venv .venv-win
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $python)) { throw "Could not create the virtual environment" }
}
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $python -m pip install -r requirements-dev.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Installing dependencies failed" }

if (-not $SkipTests) {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
}

& $python -m PyInstaller --noconfirm --clean packaging\PokerPractice.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# Verify the packaged executable with an isolated data directory.
$data = Join-Path $env:TEMP ("PokerPracticeSelfTest-" + [guid]::NewGuid())
$env:POKER_PRACTICE_DATA_DIR = $data
foreach ($run in 1, 2) {
    $process = Start-Process dist\PokerPractice\PokerPractice.exe -ArgumentList "--self-test" -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Get-Content (Join-Path $data "logs\poker_practice.log") -Tail 40
        throw "Self-test run $run failed"
    }
}
Select-String -Path (Join-Path $data "logs\poker_practice.log") -Pattern "Self-test: " | ForEach-Object { $_.Line }
Remove-Item Env:POKER_PRACTICE_DATA_DIR
Write-Host "Built and verified: dist\PokerPractice\PokerPractice.exe"
