"""verify_qr_rt.py - decode raycast_qr.png and confirm it matches raycast.com.
QR stores the LZSS-compressed bytes of raycast.com; decode -> decompress -> compare.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import lzss

from PIL import Image
import zxingcpp

qr = os.path.join(ROOT, "build", "raycast_qr.png")
raw = open(os.path.join(ROOT, "build", "raycast.com"), "rb").read()

bars = zxingcpp.read_barcodes(Image.open(qr))
print("barcodes found:", len(bars))
if not bars:
    sys.exit("no barcode found in " + qr)
payload = bars[0].bytes
print("decoded payload bytes:", len(payload))

comp = lzss.compress(raw)
ok1 = payload == comp
decomp = lzss.decompress(payload, len(raw))
ok2 = decomp == raw
print("QR payload == lzss(raycast.com):", ok1)
print("decompress(payload) == raycast.com:", ok2)
print("ROUND-TRIP:", ok1 and ok2)

# build.ps1 runs this as a step and stops when a step reports failure, so the
# exit code has to carry the result rather than the text above.
sys.exit(0 if (ok1 and ok2) else 1)