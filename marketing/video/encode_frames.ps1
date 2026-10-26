param(
    [Parameter(Mandatory = $true)][string]$FrameDirectory,
    [Parameter(Mandatory = $true)][string]$OutputFile,
    [ValidateRange(1, 60)][int]$Fps = 10,
    [ValidateRange(100000, 8000000)][int]$Bitrate = 1200000
)

$ErrorActionPreference = "Stop"
$encoderSource = Join-Path $PSScriptRoot "MediaFoundationVideoEncoder.cs"
if (-not (Test-Path -LiteralPath $encoderSource -PathType Leaf)) {
    throw "The Media Foundation encoder source is missing."
}
if (-not (Test-Path -LiteralPath $FrameDirectory -PathType Container)) {
    throw "The video frame directory is missing."
}
$outputDirectory = Split-Path -Parent $OutputFile
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

Add-Type -Path $encoderSource -ReferencedAssemblies "System.Drawing"
[MediaFoundationVideoEncoder]::EncodeDirectory($FrameDirectory, $OutputFile, $Fps, $Bitrate)
if (-not (Test-Path -LiteralPath $OutputFile -PathType Leaf)) {
    throw "Media Foundation returned without writing the output MP4."
}
Write-Output ("MP4_ENCODED bytes={0} fps={1} frames={2}" -f (Get-Item -LiteralPath $OutputFile).Length, $Fps, (Get-ChildItem -LiteralPath $FrameDirectory -Filter "frame-*.png" -File).Count)
