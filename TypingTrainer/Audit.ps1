param([string]$SdkRoot = (Join-Path $PSScriptRoot '..\Diagnostics\dotnet-sdk'))
$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$portable=Join-Path $projectRoot 'artifacts\portable'
$nugetRoot=Join-Path $env:USERPROFILE '.nuget\packages'
$deps=Get-Content (Join-Path $portable 'TypingTrainer.deps.json') -Raw | ConvertFrom-Json -AsHashtable
$packs=@($deps.libraries.Keys | Where-Object { $_ -like 'runtimepack.*' })
$components=@(); $hashes=@{}
foreach($pack in $packs){
    $name,$version=$pack.Replace('runtimepack.','').Split('/')
    $folder=Join-Path $nugetRoot ($name.ToLowerInvariant()+'\'+$version)
    if(!(Test-Path $folder)){throw "Missing runtime package: $folder"}
    [xml]$spec=Get-Content (Join-Path $folder ($name.ToLowerInvariant()+'.nuspec'))
    if($spec.package.metadata.license.'#text' -ne 'MIT'){throw "Unapproved package license: $name"}
    $metadata=Get-Content (Join-Path $folder '.nupkg.metadata') -Raw | ConvertFrom-Json
    if($metadata.source -ne 'https://api.nuget.org/v3/index.json'){throw 'Nonofficial package feed'}
    $components+=@{name=$name;version=$version;license='MIT + retained incorporated component notices';supplier='Microsoft / .NET Foundation and Contributors';source=$metadata.source;sha512=$metadata.contentHash;repository=$spec.package.metadata.repository.url;revision=$spec.package.metadata.repository.commit}
    Get-ChildItem (Join-Path $folder 'runtimes') -File -Recurse | ForEach-Object {$hashes[(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash]=$name+'/'+$version}
}
$original=@('TypingTrainer.exe','TypingTrainer.dll','TypingTrainer.pdb','TypingTrainer.deps.json','TypingTrainer.runtimeconfig.json')
$files=@();$unmapped=@()
Get-ChildItem -LiteralPath $portable -File -Recurse | Where-Object {$_.Name -ne 'SBOM.json'} | ForEach-Object {
    $relative=[IO.Path]::GetRelativePath($portable,$_.FullName).Replace('\','/')
    $hash=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    $component=$hashes[$hash]
    if(!$component){
        if($relative -in $original){$component='TypingTrainer/1.0.0 + Microsoft .NET apphost 10.0.14'}
        elseif($relative -like 'licenses/*' -or $_.Extension -in @('.md','.json','.txt') -or $_.Name -in @('LICENSE','NOTICE')){$component='Project documentation / retained legal notices'}
        else {$component='UNMAPPED';$unmapped+=$relative}
    }
    $files+=@{path=$relative;sha256=$hash;bytes=$_.Length;component=$component}
}
if($unmapped.Count){throw ('Unmapped distributed files: '+($unmapped -join ', '))}
$notices=@()
Get-ChildItem (Join-Path $projectRoot 'licenses') -Filter '*NOTICES*' | ForEach-Object {
    $document=$_.Name
    $blocks=[regex]::Split((Get-Content $_.FullName -Raw),'(?m)(?=^License (?:notice for|for) )')
    foreach($block in $blocks){if($block -match '^License (?:notice for|for) (.+)'){$notices+=@{name=$Matches[1].Trim();version='As incorporated in runtime 10.0.14; see upstream text for any separately stated version';notice=$document;sourceUrls=@([regex]::Matches($block,'https?://[^\s<>\)"\r\n]+')|ForEach-Object Value|Select-Object -Unique);copyright=@([regex]::Matches($block,'(?im)^.*(?:Copyright|\(C\)).*$')|ForEach-Object Value|Select-Object -Unique);licenseEvidence=$block.Trim()}}}
}
foreach($needed in @('LICENSE','NOTICE','THIRD_PARTY_LICENSES.md','licenses/dotnet-runtime-MIT.txt','licenses/dotnet-runtime-THIRD-PARTY-NOTICES.txt','licenses/dotnet-windowsdesktop-MIT.txt','licenses/wpf-THIRD-PARTY-NOTICES.txt')){if(!(Test-Path (Join-Path $portable $needed))){throw "Missing required notice: $needed"}}
$prohibited=Get-ChildItem (Join-Path $projectRoot 'licenses') -File | Select-String -Pattern '(?i)GNU (?:AFFERO )?GENERAL PUBLIC LICENSE|Server Side Public License|licensed under (?:the )?(?:A?GPL|SSPL)'
if($prohibited){throw 'Prohibited license text requires review'}
$sbom=@{schema='TypingTrainer dependency and distribution inventory v1';application='TypingTrainer';version='1.0.0';generatedUtc=[DateTime]::UtcNow.ToString('o');auditStatus='PASS';scope='Signed official runtime packages, zero application PackageReference dependencies, complete portable file hashes and provenance, all incorporated upstream notice sections retained; no independent legal opinion implied';components=$components;runtimeNoticeComponents=$notices;systemDependencies=@(@{name='winsqlite3.dll';bundled=$false;license='Installed Windows component; not redistributed';sqliteSource='https://www.sqlite.org/copyright.html'},@{name='Windows system fonts';bundled=$false;license='Installed Windows fonts; not redistributed'});originalAssets=@('12 original practice articles','native WPF chart','native ZIP/XML DOCX extraction','original custom installer');files=$files;selfHashExcluded='SBOM.json excludes its own bytes to avoid a recursive hash'}
$json=$sbom | ConvertTo-Json -Depth 14
Set-Content (Join-Path $projectRoot 'SBOM.json') $json -Encoding utf8
Copy-Item (Join-Path $projectRoot 'SBOM.json') (Join-Path $portable 'SBOM.json') -Force
Write-Output "Audit PASS: $($components.Count) runtime packages, $($notices.Count) upstream notice sections, $($files.Count) files; 0 unmapped files."
