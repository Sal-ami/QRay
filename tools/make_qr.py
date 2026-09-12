"""make_qr.py - Compress the COM game and encode it into a QR PNG.

Takes build/raycast.com, LZSS-compresses it and emits the smallest symbol that
holds the result at ECC level L in byte mode.  2953 bytes is the version 40
ceiling and the game is nowhere near it, so the encoder picks the version.
Lossless by construction: decode the PNG and compare to the .com.
"""
import os, sys, io, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
DATA = os.path.join(BUILD, "raycast.com")

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L
except Exception as e:
    sys.exit("qrcode lib not installed: pip install qrcode")

# ---- LZSS compress (reuse tools/lzss.py) ----
sys.path.insert(0, os.path.join(ROOT, "tools"))
import lzss

raw = open(DATA, "rb").read()
comp = lzss.compress(raw)
print("raw=%d  lzss=%d  limit=2953  fits=%s" % (len(raw), len(comp), len(comp) <= 2953))
if len(comp) > 2953:
    sys.exit("TOO BIG for QR v40-L")

# ---- lossless verification: decompress and compare ----
if lzss.decompress(comp, len(raw)) != raw:
    sys.exit("LZSS round-trip FAILED")

# ---- QR encode as raw byte mode payload (the compressed bytes). ----
# Store as raw bytes data to be scanned. Some scanners need a mode header;
# qrcode handles byte mode automatically. To be phone-friendly we also let
# qrcode pick the smallest version that fits (auto), which may be < v40.
qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_L, border=4)
qr.add_data(comp, optimize=0)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
out = os.path.join(BUILD, "raycast_qr.png")
img.save(out)
print("version=%s  QR size=%s" % (qr.version, img.size))
print("mode=byte  ECC=L  payload=%d" % len(comp))
print("saved", out)