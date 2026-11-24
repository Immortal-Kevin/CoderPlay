param(
    [string]$Dotnet = 'dotnet'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$release = Join-Path $root ('artifacts/build-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$portable = Join-Path $release 'DesktopGoose'
New-Item -ItemType Directory -Path $release | Out-Null
$dotnetPath = (Get-Command $Dotnet -ErrorAction Stop).Source
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'

& $dotnetPath publish (Join-Path $root 'App/App.csproj') -c Release -r win-x64 --self-contained true -o $portable
if ($LASTEXITCODE) { throw "dotnet publish failed ($LASTEXITCODE)" }
Get-ChildItem $portable -Filter '*.pdb' | Remove-Item
Copy-Item -LiteralPath @(
    (Join-Path $root 'LICENSE'), (Join-Path $root 'THIRD_PARTY_NOTICES.md'),
    (Join-Path $root 'README.md')
) -Destination $portable

Push-Location $portable
try {
    $licenses = New-Item -ItemType Directory -Path 'licenses'
    $deps = Get-Content -Raw DesktopGoose.deps.json | ConvertFrom-Json -AsHashtable
    $packages = if ($env:NUGET_PACKAGES) { $env:NUGET_PACKAGES } else {
        Join-Path ([Environment]::GetFolderPath('UserProfile')) '.nuget/packages'
    }
    foreach ($component in @('Microsoft.NETCore.App', 'Microsoft.WindowsDesktop.App')) {
        $dependency = $deps.libraries.Keys | Where-Object { $_ -like "runtimepack.$component.Runtime.win-x64/*" }
        if (-not $dependency) { throw "Missing runtime in dependency manifest: $component" }
        $package = Join-Path $packages $dependency.Substring("runtimepack.".Length).ToLowerInvariant()
        $componentDir = New-Item -ItemType Directory -Path (Join-Path $licenses $component)
        $files = @(Get-ChildItem -LiteralPath $package -File | Where-Object { $_.Name -match '^(LICENSE|THIRD-PARTY-NOTICES)' })
        if ($files.Length -eq 0) { throw "Missing license files for $dependency" }
        $files | Copy-Item -Destination $componentDir
        Add-Content (Join-Path $licenses 'runtime-versions.txt') $dependency
    }
}
finally { Pop-Location }

$zip = Join-Path $release 'DesktopGoose-v1.0.0-win-x64-portable.zip'
$msi = Join-Path $release 'DesktopGoose-v1.0.0-win-x64.msi'
& tar.exe -a -cf $zip -C $release 'DesktopGoose'
if ($LASTEXITCODE) { throw "Portable ZIP creation failed ($LASTEXITCODE)" }
& (Join-Path $root 'Installer/Build-Msi.ps1') -Payload $portable -Output $msi
# Windows can briefly retain a handle while opening a freshly written MSI.
$hashes = @()
foreach ($file in @($zip, $msi)) {
    for ($attempt = 0; ; $attempt++) {
        try {
            $hashes += Get-FileHash -Algorithm SHA256 -LiteralPath $file
            break
        }
        catch [IO.IOException] {
            if ($attempt -ge 9) { throw }
            Start-Sleep -Milliseconds 300
        }
    }
}
$hashes | ForEach-Object {
    $_.Hash.ToLowerInvariant() + '  ' + [IO.Path]::GetFileName($_.Path)
} | Set-Content -LiteralPath (Join-Path $release 'SHA256SUMS.txt') -Encoding ascii
Get-ChildItem -File $release | Select-Object Name, Length, FullName
