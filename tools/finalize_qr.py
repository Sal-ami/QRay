#!/usr/bin/env python3
"""finalize_qr.py - verify payload pipeline + emit v40 QR + lossless check.

Pipeline: game.html --deflate-raw--> base32 --> embed in wrapper -->
percent-encode = data:text/html,<pct(wrapper)> = QR payload.  Verify:
percent-decode the wrapper, pull the embedded base32 blob, inflate raw
(windowBits -15), compare to game.html. Then QR-encode the URI (v40-L) and
decode the PNG with zxing++ to prove lossless recovery of the exact URI.

The outer layer is percent-encoding, not base64: the wrapper is ~90% blob whose
alphabet is URI-safe, so the second base64 pass used to re-tax the whole payload
at 4/3 (2196 chars -> 2928), while percent-encoding only pays 3 bytes for the
characters that actually need escaping.  v10 stored base64's '+' as '-'; v13
removed that hack entirely by moving the blob to base32, all of whose
characters are URI-safe.

v13: the payload is no longer measured in CHARACTERS.  qrcode is asked for
optimize=20, so its segment optimizer splits the payload by mode: the base32
blob goes into an ALPHANUMERIC segment (5.5 bits/char) and the wrapper's JS
stays Byte (8 bits/char).  That is why a 3547-character payload fits a symbol
whose byte-mode ceiling is 2953 bytes, and why qr.make(fit=False) - which
raises DataOverflowError if it does not fit - is the real gate here.
"""
import os, base64, re, sys, zlib, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import qrcode
from qrcode.constants import ERROR_CORRECT_L
from qrcode.util import (MODE_NUMBER, MODE_ALPHA_NUM, MODE_8BIT_BYTE, MODE_KANJI)

AL = "0123456789ABCDEFGHIJKLMNOPQRSTUV"


def unb32(s):
    """mirror of the wrapper's JS decoder: 5 bits per char, MSB first, tail dropped"""
    bits = "".join(format(AL.index(c), "05b") for c in s)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits) - 7, 8))


payload = open(os.path.join(ROOT, "build", "payload.txt"), encoding="utf-8").read().strip()
html = open(os.path.join(ROOT, "game.html"), encoding="utf-8").read()

# ---- 1. payload is data:text/html,<percent-encoded wrapper> ----
PREFIX = "data:text/html,"
assert payload.startswith(PREFIX), "payload must be a percent-encoded data URI"
wrapper = urllib.parse.unquote(payload[len(PREFIX):])
assert urllib.parse.quote(wrapper, safe="/=._-~()*!$&'@,;") == payload[len(PREFIX):], \
    "payload is not the canonical percent-encoding of its wrapper"
m = re.search(r"s='([^']+)'", wrapper)
comp = unb32(m.group(1))
decomp = zlib.decompress(comp, -15).decode("ascii")
ok1 = decomp == html
print("PAYLOAD->wrapper->deflate-raw->game round-trip:", ok1)

# ---- 2. QR encode the URI ----
qr = qrcode.QRCode(version=40, error_correction=ERROR_CORRECT_L, border=4)
qr.add_data(payload, optimize=20)
qr.make(fit=False)          # raises DataOverflowError if it does not fit v40-L
img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
out = os.path.join(ROOT, "build", "web_qr.png")
img.save(out)
print("QR v40 modules=%d -> %s" % (qr.modules_count, out))
names = {MODE_NUMBER: "Numeric", MODE_ALPHA_NUM: "Alphanumeric",
         MODE_8BIT_BYTE: "Byte", MODE_KANJI: "Kanji"}
count = {"Numeric": 14, "Alphanumeric": 13, "Byte": 16, "Kanji": 12}
bpc = {"Numeric": 3.33, "Alphanumeric": 5.5, "Byte": 8, "Kanji": 13}
used = 0
for d in qr.data_list:
    mode, n = names[d.mode], len(d.data)
    used += 4 + count[mode] + n * bpc[mode]
    print("  segment %-13s %5d chars" % (mode, n))
print("  bits %d of %d -> spare %.0f bytes-equivalent"
      % (used, 2956 * 8, (2956 * 8 - used) / 8))

# ---- 3. decode QR PNG and confirm exact URI ----
from PIL import Image
import zxingcpp
bars = zxingcpp.read_barcodes(Image.open(out))
decoded = bars[0].bytes.decode()
ok2 = decoded == payload
print("QR decode == payload:", ok2)
print("FINAL:", ok1 and ok2, " payload chars:", len(payload))
sys.exit(0 if (ok1 and ok2) else 1)