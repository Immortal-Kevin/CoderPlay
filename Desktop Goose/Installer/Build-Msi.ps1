param(
    [Parameter(Mandatory)][string]$Payload,
    [Parameter(Mandatory)][string]$Output
)

$ErrorActionPreference = 'Stop'
$Payload = (Resolve-Path -LiteralPath $Payload).Path
$Output = [IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $Output) { throw "The output already exists: $Output" }
$work = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ('DesktopGooseMsi-' + [guid]::NewGuid().ToString('N')))
$cab = Join-Path $work 'goose.cab'
$product = '{507A54D9-D524-4B52-8F0E-65358A061B51}'
$upgrade = '{80C8CB93-8A51-490A-AF25-E5754E808BA4}'
# File identifiers depend on relative paths so files retain component identity across builds.
function Id([string]$value) {
    [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($value.ToLowerInvariant()))).Substring(0, 24)
}
function ComponentGuid([string]$value) {
    '{' + [guid]::ParseExact((Id $value) + 'E24853F9', 'N').ToString().ToUpperInvariant() + '}'
}
$dirs = [Collections.Generic.List[string]]::new()
$dirs.Add("TARGETDIR		SourceDir")
$dirs.Add("LocalAppDataFolder	TARGETDIR	.")
$dirs.Add("Programs	LocalAppDataFolder	Programs")
$dirs.Add("INSTALLFOLDER	Programs	DESKTO~1|DesktopGoose")
$dirs.Add("ProgramMenuFolder	TARGETDIR	.")
$dirs.Add("GooseMenu	ProgramMenuFolder	CODERP~1|CoderPlay Desktop Goose")
$dirIds = @{ '.' = 'INSTALLFOLDER' }
function DirectoryId([string]$relative) {
    if ($dirIds.ContainsKey($relative)) { return $dirIds[$relative] }
    $parent = [IO.Path]::GetDirectoryName($relative)
    if ([string]::IsNullOrEmpty($parent)) { $parent = '.' }
    $parentId = DirectoryId $parent
    $id = 'd' + (Id $relative)
    $short = 'D' + $id.Substring(1, 7)
    $name = [IO.Path]::GetFileName($relative)
    $dirs.Add("$id	$parentId	$short|$name")
    $dirIds[$relative] = $id
    return $id
}

function Call($object, [string]$method, [object[]]$argsList) {
    $object.GetType().InvokeMember($method, 'InvokeMethod', $null, $object, $argsList)
}
function SetCom($object, [string]$property, [object[]]$argsList) {
    $object.GetType().InvokeMember($property, 'SetProperty', $null, $object, $argsList)
}
function GetCom($object, [string]$property, [object[]]$argsList) {
    $object.GetType().InvokeMember($property, 'GetProperty', $null, $object, $argsList)
}
function ImportTable([string]$name, [string]$header, [string]$types, [string]$keys, [string[]]$rows) {
    $file = "$name.idt"
    $content = @($header, $types, "$name	$keys") + $rows
    [IO.File]::WriteAllLines((Join-Path $work $file), $content, [Text.Encoding]::ASCII)
    Call $database 'Import' @($work.FullName, $file)
}
function Stream([string]$name, [string]$file) {
    $view = Call $database 'OpenView' @('SELECT `Name`, `Data` FROM `_Streams`')
    $record = Call $installer 'CreateRecord' @(2)
    SetCom $record 'StringData' @(1, $name)
    Call $record 'SetStream' @(2, $file)
    Call $view 'Execute' @()
    Call $view 'Modify' @(1, $record)
    Call $view 'Close' @()
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($record)
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($view)
}

$files = [Collections.Generic.List[string]]::new()
$components = [Collections.Generic.List[string]]::new()
$links = [Collections.Generic.List[string]]::new()
$ddf = [Collections.Generic.List[string]]::new()
$report = Join-Path $work 'cab-report.txt'
$inf = Join-Path $work 'cab-files.inf'
foreach ($line in @('.OPTION EXPLICIT', '.Set Cabinet=on', '.Set Compress=on',
    '.Set CompressionType=MSZIP', '.Set MaxDiskSize=0',
    '.Set CabinetNameTemplate=goose.cab', ".Set DiskDirectoryTemplate=""$work""",
    ".Set RptFileName=""$report""", ".Set InfFileName=""$inf""")) { $ddf.Add($line) }

$sequence = 0
$appFile = $null
foreach ($item in Get-ChildItem -LiteralPath $Payload -File -Recurse | Sort-Object FullName) {
    $relative = [IO.Path]::GetRelativePath($Payload, $item.FullName)
    $dir = [IO.Path]::GetDirectoryName($relative)
    if ([string]::IsNullOrEmpty($dir)) { $dir = '.' }
    $directory = DirectoryId $dir
    $suffix = Id $relative
    $file = 'f' + $suffix
    $component = 'c' + $suffix
    $guid = ComponentGuid $relative
    $short = 'G' + $suffix.Substring(0, 7) + '.FIL'
    $sequence++
    $files.Add("$file	$component	$short|$($item.Name)	$($item.Length)			512	$sequence")
    $components.Add("$component	$guid	$directory	256		$file")
    $links.Add("Main	$component")
    $ddf.Add(('"{0}" {1}' -f $item.FullName, $file))
    if ($relative -eq 'DesktopGoose.exe') { $appFile = $file }
}
if (-not $appFile) { throw 'DesktopGoose.exe is missing.' }
$menuGuid = ComponentGuid 'start-menu'
$components.Add("StartMenu	$menuGuid	GooseMenu	260		MenuKey")
$links.Add("Main	StartMenu")
$ddfPath = Join-Path $work 'goose.ddf'
[IO.File]::WriteAllLines($ddfPath, $ddf, [Text.Encoding]::Default)
& makecab.exe /F $ddfPath | Out-Null
if ($LASTEXITCODE -or -not (Test-Path -LiteralPath $cab)) { throw 'makecab failed.' }

$installer = New-Object -ComObject WindowsInstaller.Installer
$database = Call $installer 'OpenDatabase' @($Output, 3)
$properties = @(
    "ProductCode	$product", "UpgradeCode	$upgrade", "ProductName	Desktop Goose", "ProductVersion	1.0.0",
    "Manufacturer	CoderPlay", "ProductLanguage	1033", "ARPNOMODIFY	1"
)
ImportTable 'Property' "Property	Value" "s72	L0" 'Property' $properties
ImportTable 'Directory' "Directory	Directory_Parent	DefaultDir" "s72	S72	l255" 'Directory' $dirs
ImportTable 'Component' "Component	ComponentId	Directory_	Attributes	Condition	KeyPath" "s72	S38	s72	i2	S255	S72" 'Component' $components
ImportTable 'File' "File	Component_	FileName	FileSize	Version	Language	Attributes	Sequence" "s72	s72	l255	i4	S72	S20	I2	i2" 'File' $files
ImportTable 'Feature' "Feature	Feature_Parent	Title	Description	Display	Level	Directory_	Attributes" "s38	S38	L64	L255	I2	i2	S72	i2" 'Feature' @(
    "Main		Desktop Goose	Desktop pet	1	1	INSTALLFOLDER	0"
)
ImportTable 'FeatureComponents' "Feature_	Component_" "s38	s72" "Feature_	Component_" $links
ImportTable 'Media' "DiskId	LastSequence	DiskPrompt	Cabinet	VolumeLabel	Source" "i2	i4	L64	S255	S32	S72" 'DiskId' @("1	$sequence		#goose.cab		")
ImportTable 'Registry' "Registry	Root	Key	Name	Value	Component_" "s72	i2	l255	L255	L0	s72" 'Registry' @(
    "MenuKey	1	Software\CoderPlay\DesktopGoose\Installer	Installed	#1	StartMenu"
)
ImportTable 'Shortcut' "Shortcut	Directory_	Name	Component_	Target	Arguments	Description	Hotkey	Icon_	IconIndex	ShowCmd	WkDir" "s72	s72	l128	s72	s72	S255	L255	I2	S72	I2	I2	S72" 'Shortcut' @(
    "Launch	GooseMenu	GOOSE|Desktop Goose	StartMenu	[#$appFile]		Desktop Goose				1	INSTALLFOLDER"
)
ImportTable 'RemoveFile' "FileKey	Component_	FileName	DirProperty	InstallMode" "s72	s72	L255	s72	i2" 'FileKey' @(
    "MenuFolder	StartMenu		GooseMenu	2"
)
$execute = @(
    "CostInitialize		800", "FileCost		900", "CostFinalize		1000", "InstallValidate		1400",
    "InstallInitialize		1500", "ProcessComponents		1600", "UnpublishFeatures		1800",
    "RemoveRegistryValues		2600", "RemoveShortcuts		3200", "RemoveFiles		3500",
    "InstallFiles		4000", "CreateShortcuts		4500", "WriteRegistryValues		5000",
    "RegisterUser		6000", "RegisterProduct		6100", "PublishFeatures		6300",
    "PublishProduct		6400", "InstallFinalize		6600"
)
ImportTable 'InstallExecuteSequence' "Action	Condition	Sequence" "s72	S255	I2" 'Action' $execute
Stream 'goose.cab' $cab
$summary = GetCom $database 'SummaryInformation' @(20)
SetCom $summary 'Property' @(2, 'Desktop Goose')
SetCom $summary 'Property' @(3, 'Desktop Goose 1.0.0')
SetCom $summary 'Property' @(4, 'CoderPlay')
SetCom $summary 'Property' @(7, 'x64;1033')
SetCom $summary 'Property' @(9, [guid]::NewGuid().ToString('B').ToUpperInvariant())
SetCom $summary 'Property' @(14, 500)
SetCom $summary 'Property' @(15, 10)
SetCom $summary 'Property' @(19, 2)
Call $summary 'Persist' @()
Call $database 'Commit' @()
[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($summary)
[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($database)
[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($installer)
$verifiedWork = (Resolve-Path -LiteralPath $work).Path
if ((Split-Path -Parent $verifiedWork) -eq (Resolve-Path -LiteralPath $env:TEMP).Path -and
    (Split-Path -Leaf $verifiedWork) -match '^DesktopGooseMsi-[a-f0-9]{32}$') {
    Remove-Item -LiteralPath $verifiedWork -Recurse
}
