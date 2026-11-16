param([string]$DotNet='dotnet')
$ErrorActionPreference='Stop'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$root=$PSScriptRoot
function Run([string[]]$Arguments){& $DotNet @Arguments;if($LASTEXITCODE -ne 0){throw ('dotnet failed: '+($Arguments -join ' '))}}
Run -Arguments @('run','--project',"$root\tests\TypingTrainer.Tests.csproj",'-c','Release')
Run -Arguments @('run','--project',"$root\ui-tests\UiTests.csproj",'-c','Release','--',"$root\reports\ui")
Run -Arguments @('publish',"$root\src\TypingTrainer.csproj",'-c','Release','-r','win-x64','--self-contained','true','-o',"$root\artifacts\portable")
Copy-Item "$root\LICENSE","$root\NOTICE","$root\README.md","$root\THIRD_PARTY_LICENSES.md","$root\DISTRIBUTION_CHECK.md","$root\TEST_REPORT.md" "$root\artifacts\portable" -Force
Copy-Item "$root\licenses" "$root\artifacts\portable" -Recurse -Force
$sdkRoot=Split-Path (Get-Command $DotNet).Source
& "$root\Audit.ps1" -SdkRoot $sdkRoot
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive="$root\artifacts\TypingTrainer-1.0.0-win-x64.zip"
if(Test-Path $archive){Remove-Item -LiteralPath $archive}
[IO.Compression.ZipFile]::CreateFromDirectory("$root\artifacts\portable",$archive,[IO.Compression.CompressionLevel]::Optimal,$false)
Run -Arguments @('publish',"$root\installer\Installer.csproj",'-c','Release','-r','win-x64','--self-contained','true','-p:PublishSingleFile=true','-p:IncludeNativeLibrariesForSelfExtract=true','-p:IncludeAllContentForSelfExtract=true','-p:EnableCompressionInSingleFile=true','-p:DebugType=None','-o',"$root\artifacts\setup")
Copy-Item "$root\artifacts\setup\TypingTrainer-Setup.exe" "$root\artifacts\TypingTrainer-Setup.exe" -Force
Get-FileHash "$root\artifacts\TypingTrainer-1.0.0-win-x64.zip","$root\artifacts\TypingTrainer-Setup.exe" -Algorithm SHA256 | Select-Object Path,Hash | ConvertTo-Json | Set-Content "$root\artifacts\SHA256SUMS.json"

