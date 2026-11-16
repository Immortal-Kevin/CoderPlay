param([ValidateSet('Install','Uninstall')][string]$Phase='Install')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot;$artifacts=Join-Path $root 'artifacts';$reports=Join-Path $root 'reports';$report=Join-Path $reports 'package-tests.json'
$installation=Join-Path $env:LOCALAPPDATA 'Programs\TypingTrainer';$data=Join-Path $env:LOCALAPPDATA 'TypingTrainer';$registry='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\TypingTrainer'
$results=@();if($Phase -eq 'Uninstall' -and (Test-Path $report)){$results=@(Get-Content $report -Raw|ConvertFrom-Json)}
function Check([string]$Name,[scriptblock]$Action){try{& $Action;$script:results+=@{name=$Name;status='PASS'};Write-Output "PASS $Name"}catch{$script:results+=@{name=$Name;status='FAIL';error=$_.Exception.Message};Write-Output "FAIL $Name : $_"}}
function Snapshot(){if(Test-Path $data){@(Get-ChildItem $data -File -Recurse|ForEach-Object{[IO.Path]::GetRelativePath($data,$_.FullName)+' '+(Get-FileHash $_.FullName).Hash})-join "`n"}else{''}}
function RunExe([string]$File,[string]$Arguments){$p=Start-Process -FilePath $File -ArgumentList $Arguments -PassThru -Wait -WindowStyle Hidden;if($p.ExitCode -ne 0){throw "Exit code $($p.ExitCode)"}}
if($Phase -eq 'Install'){
 Check 'Portable ZIP hashes match audited inventory' {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $artifacts 'TypingTrainer-1.0.0-win-x64.zip'))
    try{$sbom=Get-Content (Join-Path $root 'SBOM.json') -Raw|ConvertFrom-Json;foreach($file in $sbom.files){$entry=$zip.GetEntry($file.path);if(!$entry){throw "Missing $($file.path)"};$stream=$entry.Open();try{$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream));if($hash -ne $file.sha256){throw "Hash mismatch: $($file.path)"}}finally{$stream.Dispose()}};if(!$zip.GetEntry('SBOM.json')){throw 'Missing SBOM'}}finally{$zip.Dispose()}
 }
 Check 'Self-contained runtime metadata' {$config=Get-Content (Join-Path $artifacts 'portable\TypingTrainer.runtimeconfig.json') -Raw|ConvertFrom-Json;if(!$config.runtimeOptions.includedFrameworks -or $config.runtimeOptions.frameworks){throw 'Not self contained'}}
 Check 'Installer embedded payload readable' {RunExe (Join-Path $artifacts 'TypingTrainer-Setup.exe') '--verify-payload'}
 $before=Snapshot
 Check 'Silent current-user installation' {if(Test-Path $installation){throw 'Pre-existing install directory; test refused to overwrite it'};RunExe (Join-Path $artifacts 'TypingTrainer-Setup.exe') '--silent'}
 Check 'Installed files match portable SHA256' {$sbom=Get-Content (Join-Path $root 'SBOM.json') -Raw|ConvertFrom-Json;foreach($file in $sbom.files){$p=Join-Path $installation $file.path;if(!(Test-Path $p) -or (Get-FileHash $p).Hash -ne $file.sha256){throw "Installed hash mismatch: $($file.path)"}}}
 Check 'Start menu shortcut and uninstall registration' {if(!(Test-Path $registry)){throw 'No uninstall registration'};if(!(Test-Path (Join-Path ([Environment]::GetFolderPath('Programs')) 'Typing Trainer.lnk'))){throw 'No shortcut'}}
 Check 'Installation preserves training data' {if((Snapshot) -ne $before){throw 'User data changed'}}
}else{
 $before=Snapshot
 Check 'Silent uninstall removes original app files' {RunExe (Join-Path $installation 'Uninstall.exe') '--uninstall --silent';$end=[DateTime]::UtcNow.AddSeconds(20);while((Test-Path $installation) -and [DateTime]::UtcNow -lt $end){Start-Sleep -Milliseconds 200};if(Test-Path $installation){throw 'Installation directory remains'}}
 Check 'Uninstall removes registration and shortcut' {if(Test-Path $registry){throw 'Registry remains'};if(Test-Path (Join-Path ([Environment]::GetFolderPath('Programs')) 'Typing Trainer.lnk')){throw 'Shortcut remains'}}
 Check 'Uninstall preserves training data' {if((Snapshot) -ne $before){throw 'User data changed'}}
}
ConvertTo-Json -InputObject @($results) -Depth 5|Set-Content $report
if(@($results|Where-Object {$_.status -eq 'FAIL'}).Count){exit 1}
