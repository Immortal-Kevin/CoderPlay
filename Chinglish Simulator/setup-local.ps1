$ErrorActionPreference = 'Stop'
$root = Join-Path $env:LOCALAPPDATA 'Chinglish Simulator\inference'
New-Item -ItemType Directory -Path $root -Force | Out-Null

function Get-Sha256($Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '')
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}

function Get-VerifiedFile($Url, $Path, $Hash, $Size) {
    if ((Test-Path -LiteralPath $Path) -and ((Get-Sha256 $Path) -eq $Hash)) {
        return
    }
    $partial = "$Path.partial"
    if (!(Test-Path -LiteralPath $partial) -or (Get-Item -LiteralPath $partial).Length -ne $Size) {
        & curl.exe -fL --retry 3 -C - -o $partial $Url
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
    }
    if ((Get-Sha256 $partial) -ne $Hash) {
        Remove-Item -LiteralPath $partial
        throw 'SHA-256 verification failed. Run setup again to redownload the file.'
    }
    Move-Item -LiteralPath $partial -Destination $Path -Force
}

$engine = Join-Path $root 'llama-b12466'
$archive = Join-Path $root 'llama.zip'
$cli = Join-Path $engine 'llama-completion.exe'
if (!(Test-Path -LiteralPath $cli)) {
    Get-VerifiedFile 'https://github.com/ggml-org/llama.cpp/releases/download/b12466/llama-b12466-bin-win-vulkan-x64.zip' $archive '108FC23FBE10D15548246B7E3793A7DFE6375F9DDD210CCF9830318AF54A9FED' 38354267
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $staging = Join-Path $root ('engine-' + [guid]::NewGuid())
    [IO.Compression.ZipFile]::ExtractToDirectory($archive, $staging)
    Move-Item -LiteralPath $staging -Destination $engine
    Remove-Item -LiteralPath $archive
}
Get-VerifiedFile 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q5_k_m.gguf' (Join-Path $root 'qwen2.5-1.5b-instruct-q5_k_m.gguf') 'B46661073C18E5B56A41FA320975F866A00DEF1FF08FEEF4718E013258896F8C' 1285494304
& $cli --list-devices
if ($LASTEXITCODE -ne 0) { throw 'Could not list Vulkan devices.' }
Write-Host 'Local files are ready. Launch Chinglish Simulator.exe.'
