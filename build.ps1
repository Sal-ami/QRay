# build.ps1 - rebuild every artifact in this repo from the sources.
#
#   powershell -File build.ps1              # everything
#   powershell -File build.ps1 -AsmOnly     # just the QR holding the x86 game
#
# Needs nasm and python on PATH.  python needs the qrcode, pillow and zxing-cpp
# packages:
#   pip install qrcode pillow zxing-cpp
param([switch]$AsmOnly)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Need($exe, $hint) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        throw "$exe is not on PATH.  $hint"
    }
}

Need 'nasm'   'Get it from https://www.nasm.us/'
Need 'python' 'Get it from https://www.python.org/'

# The v40-L byte mode ceiling.  The game is far under it, which is the point:
# the governor is here so that adding maze or sprites cannot silently push the
# program past what a QR symbol can hold.
$qrCeiling = 2953

# Every step is checked.  python exits nonzero when a script raises and the
# scripts that can miss their target exit nonzero when they do, so a build that
# breaks an artifact stops here instead of printing a failure and leaving the
# bad artifact in build/ for someone to hand out.
function Step($what, $exe, $argv) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) { throw "$what failed with exit code $LASTEXITCODE" }
}

# src/raycast.asm is one self contained NASM file, so the whole engine, the
# maze, the palette and the art come out of a single -f bin pass.
#
# -d com_file assembles for org 0x100, which is the address DOS loads a .com
# image at and therefore the address the three absolute table references in the
# program (sin_table, mini_map and doom_pal) have to resolve against.  Without
# the define the source assembles at the boot sector origin 0x7c00 it inherited
# from cubicDoom, and an image built that way cannot run under DOS: those three
# references then point about 0x7b00 bytes past the end of the program.
Step 'nasm' 'nasm' @('-f', 'bin', '-d', 'com_file',
                     (Join-Path $root 'src\raycast.asm'),
                     '-o', (Join-Path $root 'build\raycast.com'))
Step 'lzss' 'python' @((Join-Path $root 'tools\lzss.py'), 'compress',
                       (Join-Path $root 'build\raycast.com'),
                       (Join-Path $root 'build\raycast.lz'))

$raw = (Get-Item (Join-Path $root 'build\raycast.com')).Length
$lz  = (Get-Item (Join-Path $root 'build\raycast.lz')).Length
Write-Host ("game: {0} bytes of machine code, {1} bytes compressed, {2} left under the ceiling" -f $raw, $lz, ($qrCeiling - $lz))
if ($lz -gt $qrCeiling) { throw "size governor: $lz compressed bytes is over the $qrCeiling byte ceiling" }

Step 'make_qr'      'python' @((Join-Path $root 'tools\make_qr.py'))       # build/raycast_qr.png
Step 'verify_qr_rt' 'python' @((Join-Path $root 'tools\verify_qr_rt.py'))  # decode the PNG back and compare

if ($AsmOnly) { exit 0 }

# The browser build: the same game rewritten as a page that fits the same way.
Step 'write_g4'     'python' @((Join-Path $root 'tools\write_g4.py'))      # src/game.js
Step 'make_browser' 'python' @((Join-Path $root 'tools\make_browser.py'))  # game.html + build/payload.txt
Step 'finalize_qr'  'python' @((Join-Path $root 'tools\finalize_qr.py'))   # build/web_qr.png
