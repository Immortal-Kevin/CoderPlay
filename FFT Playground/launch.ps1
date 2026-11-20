param([switch]$Diagnostic, [string]$PythonPath)
$ErrorActionPreference = 'Stop'
try {
    $localData = $env:LOCALAPPDATA
    if (-not $localData) { $localData = [Environment]::GetFolderPath('LocalApplicationData') }
    $logRoot = Join-Path $localData 'FFT Playground\logs'
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    $logPath = Join-Path $logRoot 'launcher.log'
    function Write-Diagnostic([string]$message) {
        Write-Host $message
        Add-Content -LiteralPath $logPath -Value $message -Encoding UTF8
    }
    Set-Content -LiteralPath $logPath -Value ('FFT Playground launcher ' + (Get-Date -Format o)) -Encoding UTF8
    Write-Diagnostic ('Project: ' + $PSScriptRoot)
    # Child-process environment only; user/system settings are not modified.
    foreach ($name in @('PYTHONHOME','PYTHONPATH','TCL_LIBRARY','TK_LIBRARY')) {
        if (Test-Path "Env:$name") {
            Write-Diagnostic ('Ignoring inherited ' + $name + ' for interpreter isolation')
            Remove-Item -LiteralPath "Env:$name"
        }
    }
    $candidates = [Collections.Generic.List[string]]::new()
    function Add-Candidate([string]$path) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf) -and -not $candidates.Contains($path)) {
            $candidates.Add($path)
        }
    }
    Add-Candidate (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try { $inventory = & $py.Source -0p 2>&1 } catch {
            Write-Diagnostic ('Python launcher inventory unavailable: ' + $_.Exception.Message)
            $inventory = @()
        }
        foreach ($line in $inventory) {
            if ([string]$line -match '([A-Za-z]:\\.*\\python(?:3)?\.exe)\s*$') { Add-Candidate $Matches[1] }
        }
    }
    foreach ($command in @(Get-Command python.exe -All -ErrorAction SilentlyContinue)) {
        if ($command.Source -notlike '*\WindowsApps\*') { Add-Candidate $command.Source }
    }
    foreach ($registry in @('HKCU:\Software\Python','HKLM:\Software\Python','HKLM:\Software\WOW6432Node\Python')) {
        if (Test-Path $registry) {
            foreach ($key in @(Get-ChildItem $registry -Recurse -ErrorAction SilentlyContinue | Where-Object PSChildName -eq 'InstallPath')) {
                $props = Get-ItemProperty $key.PSPath
                if ($props.ExecutablePath) { Add-Candidate $props.ExecutablePath }
                $base = $key.GetValue('')
                if ($base) { Add-Candidate (Join-Path $base 'python.exe') }
            }
        }
    }
    if ($PythonPath) {
        $candidates.Clear()
        Write-Diagnostic ('Explicit interpreter requested: ' + $PythonPath)
        Add-Candidate $PythonPath
    }
    $selected = $null
    foreach ($candidate in $candidates) {
      try {
        Write-Diagnostic ('Checking: ' + $candidate)
        $start = [Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $candidate
        $start.Arguments = '-E -s "' + (Join-Path $PSScriptRoot 'startup_check.py') + '"'
        $start.WorkingDirectory = $PSScriptRoot
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $process = [Diagnostics.Process]::Start($start)
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(15000)) {
            $process.Kill()
            Write-Diagnostic 'FAIL: interpreter/Tk probe exceeded 15 seconds'
            $process.Dispose()
            continue
        }
        Write-Diagnostic $stdout.Result
        if ($stderr.Result) { Write-Diagnostic $stderr.Result }
        if ($process.ExitCode -eq 0 -and -not $selected) { $selected = $candidate }
        $process.Dispose()
        if ($selected -and -not $Diagnostic) { break }
      } catch {
        Write-Diagnostic ('FAIL probing ' + $candidate + ': ' + $_.Exception.Message)
      }
    }
    if (-not $selected) { throw 'No compatible Python 3.11+ with working Tkinter found. Install Python with Tcl/Tk support, then retry.' }
    Write-Diagnostic ('Selected interpreter: ' + $selected)
    if ($Diagnostic) {
        Write-Diagnostic ('Diagnostics complete. Log: ' + $logPath)
        Read-Host 'Press Enter to close' | Out-Null
        exit 0
    }
    Write-Diagnostic ('Launching GUI; application log: ' + (Join-Path $logRoot 'application.log'))
    & $selected -E -s (Join-Path $PSScriptRoot 'app.py')
    $result = $LASTEXITCODE
    Write-Diagnostic ('GUI exit code: ' + $result)
    if ($result -ne 0) { throw ('GUI failed with exit code ' + $result) }
    exit 0
} catch {
    $detail = ($_ | Out-String)
    Write-Host $detail -ForegroundColor Red
    if ($logPath) { Add-Content -LiteralPath $logPath -Value $detail -Encoding UTF8 }
    exit 1
}
