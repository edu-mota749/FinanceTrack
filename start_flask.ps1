$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$oldProcesses = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'FinanceTrack' -and $_.CommandLine -match 'app\.py' }

foreach ($process in $oldProcesses) {
    Stop-Process -Id $process.ProcessId -Force
}

$env:FLASK_DEBUG = 'true'
. .\.venv\Scripts\Activate.ps1
python app.py
