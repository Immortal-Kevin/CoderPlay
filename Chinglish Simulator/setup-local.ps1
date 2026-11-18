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
Get-VerifiedFile 'https://huggingface.co/jc-builds/Qwen3-4B-Instruct-2507-GGUF/resolve/4e6afbc2cf425128ec54bd934d9bf2d644e50448/Qwen3-4B-Instruct-2507-Q4_K_M.gguf' (Join-Path $root 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf') '3605803B982CB64AEAD44F6C1B2AE36E3ACDB41D8E46C8A94C6533BC4C67E597' 2497281120
& $cli --list-devices
if ($LASTEXITCODE -ne 0) { throw 'Could not list Vulkan devices.' }
Write-Host 'Local files are ready. Launch Chinglish Simulator.exe.'
