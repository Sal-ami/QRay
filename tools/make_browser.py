#!/usr/bin/env python3
"""make_browser.py - wrap game.js into a valid browser game.html + QR payload.
gzip+DecompressionStream wrapper (universal on 2026 browsers), canvas id=z
(game.js declares global var c/r/u - id-globals would clash).

v13 (mobile): the payload's INNER blob is base32 (0-9A-V), not base64.
Base64 is mixed case, so the whole payload falls back to the QR's byte mode and
inherits its 2953-byte ceiling.  A v40-L symbol, though, holds 4296 characters
in ALPHANUMERIC mode (0-9 A-Z space $ % * + - . / :), and that set is
case-insensitive - so an upper+digits alphabet is alphanumeric-eligible, and
alphanumeric costs 5.5 bits/char against byte mode's 8.  Base32 packs 5 bits
into each such char, so the blob moves at 1.1 payload-bytes per deflate byte
instead of 1.333 (still well ahead of hex's 1.375 and base64's 1.333).
Measured on this payload: 2676 base64 chars (21408 bits) -> 3212 base32 chars
(17666 bits), i.e. -468 bytes; the 89-char JS decoder that reads it back costs
129 chars of wrapper, so the net is about -400 bytes.  tools/finalize_qr.py has
to pass optimize=20 so qrcode's own segment optimizer splits the payload; it
produces Byte x30 | Alphanumeric x3212 | Byte x305 and still round-trips
through zxing++ byte-for-byte.  Proof lives in an independent probe, which also
runs the decoder under node against the real deflate stream.

v13 (mobile): the 406 bytes buy touch input, and NOTHING in src/game.js changes -
the game's pixels are the v12 pixels, which a re-golf check re-proves at 0
differing scenes.
v14 (sizing): the image FILLS the window again.  v13 had used object-fit:contain
everywhere, and a 160:100 image letterboxed inside a 16:9 window reads as "the
game got compressed" on a wide desktop and on a phone held sideways.  Filling
is object-fit's default, so the property is
simply gone and the payload got 18 chars cheaper.  The one shape where bars beat
filling is a phone held upright: a 390x844 box scales the vertical axis 8.44x
and the horizontal axis 2.44x and so @media(orientation:portrait) turns contain
shape alone.  Measured at three viewport shapes in a real engine, against
screenshot pixels and the canvas CSS box.
"""
import os, re, zlib, sys, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# base32 for URLs: the alphabet is spelled so the decoder needs no lookup table.
# parseInt(c,32) IS radix 32 over 0-9A-V, so the inner blob decodes with
# arithmetic alone.  (c-48 would coerce the STRING '0' to 0 rather than to its
# char code - measured: it decoded to garbage.)
AL = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
DEC = ("u=[],n=b=0;for(c of s)n=n*32+parseInt(c,32),b+=5,"
       "b>7&&(b-=8,u.push(n>>b&255),n&=(1<<b)-1)")

# v40-L data capacity in bits (2956 data codewords).  The gate below is a
# greedy mode-run estimate, which the qrcode lib's DP optimizer can only beat,
# so it is a safe upper bound; tools/finalize_qr.py still asserts the real thing
# by making the symbol with fit=False.
CAP_BITS = 2956 * 8


def b32(data):
    """bit-pack bytes into the alphabet above, 5 bits per character"""
    bits = "".join(format(b, "08b") for b in data)
    bits += "0" * (-len(bits) % 5)
    return "".join(AL[int(bits[i:i + 5], 2)] for i in range(0, len(bits), 5))


def qr_bits(p):
    """conservative bit cost: greedy runs of alphanumeric vs everything else"""
    alpha = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:")
    total, i, n = 0, 0, len(p)
    while i < n:
        run = p[i] in alpha
        j = i
        while j < n and (p[j] in alpha) == run:
            j += 1
        total += 4 + (13 + (j - i) * 5.5 if run else 16 + (j - i) * 8)
        i = j
    return total

js = open(os.path.join(ROOT, "src", "game.js"), encoding="utf-8").read()
js = re.sub(r"^module\.exports.*$", "", js, flags=re.M).rstrip("\n")
js = js.replace("\n", "")  # every line ends ; { or } so newline-strip is safe

boot = (
    "z.width=W;z.height=H;A=z.getContext('2d'),k={};"
    "onkeydown=onkeyup=e=>k[e.keyCode]=e.type[3]<'u';"
    # v13: touch input writes the SAME k[] the keyboard writes, so no game code
    # changes at all - step() cannot tell the two apart.  A phone has no keys,
    # so before this the payload was scan-and-unplayable.
    #   bottom strip (y>.82)  = fire (32).  It lands exactly on the status bar
    #                           band, so a thumb there never covers the 3D view.
    #   left half             = walk: up is forward (87), down is back (83).
    #   right half            = turn: inward of x=.7 is left (65), outward is
    #                           right (68), i.e. the thumb's natural reach.
    # for(t of e.touches) is what makes it a real pad: TWO thumbs can hold two
    # zones at once (walk while turning), and touchend re-derives k from the
    # fingers still down, so lifting one releases only that one.  clientX over
    # innerWidth needs no getBoundingClientRect and is scale-invariant, which
    # also means the letterbox bars take part in the zones instead of deadening.
    "ontouchstart=ontouchmove=ontouchend=e=>{k={};for(t of e.touches)"
    "x=t.clientX/innerWidth,y=t.clientY/innerHeight,"
    "k[y>.82?32:x<.5?y<.5?87:83:x<.7?65:68]=1};"
    # v11: the win/lose banner uses the CANVAS's own text engine instead of
    # glyph art.  The browser already owns a font, so "WON"/"LOST" cost 5 and 6
    # string characters where a 3x5 letter font for the same two words would
    # cost ~90 (and dg's digits cannot spell: there are no letters in the 3x5
    # font at all).  White is set ONCE at boot - the context default is black,
    # i.e. an invisible banner over the dark arena - and the per-frame fillText
    # sits AFTER putImageData because every frame is repainted from scratch.
    # x=68 centres a 10px sans-serif "LOST" (~25px wide) on the 160px canvas
    # without paying for textAlign, and y=45 is the alphabetic baseline of the
    # 3D viewport (rows 0-80), i.e. a quarter of the way up the screen.
    # al/hp are the game's own counters (render() publishes al), so the banner
    # can never disagree with the status bar: al is 0 only when every imp has
    # been shot (a corpse keeps its death timer) and hp is 0 only when the imps
    # got you.  The canvas context is bound to A, the one free one-letter global
    # in this payload - 'cv' cost a character at every one of its four uses.
    "A.fillStyle='#fff';"
    # v10: gen(seed) builds the 28x28 arena and places the player + 6 spread
    # enemies (no packed spawn table any more - placement is structural).
    # Date.now() means every run gets a different map; a generator sweep walks
    # 200 seeded maps to prove they are all connected and all spawns are valid.
    "gen(Date.now());"
    "setInterval(()=>{step(p,E,k);"
    "A.putImageData(new ImageData(render(...p,E),W,H),0,0);"
    # v13: k[32] joins k[82] as a restart trigger.  On a phone the bullets come
    # from the fire strip, so "hold the fire strip to play again" is the touch
    # equivalent of pressing R, and it only happens while hp is 0.
    "A.fillText(al?hp?'':'LOST':'WON',68,45),hp||k[82]|k[32]&&location.reload()},16);"
)

# v14: filling the window is object-fit's default, so the property is gone
# entirely (18 payload chars cheaper than v13's contain).  A 160:100 image
# letterboxed inside a 16:9 window is what reads as "compressed" on a wide
# desktop, and a phone held sideways is the same shape.  Filling a phone held
# UPRIGHT is worse than bars: a 390x844 box scales the vertical axis 8.44x and
# the horizontal axis 2.44x, so that one shape keeps contain, at the cost of 4
# escaped braces (the data URI has to write { as %7B).
html = ('<body style=margin:0;background:#000;touch-action:none>'
        '<canvas id=z style=width:100vw;height:100vh;display:block;'
        'image-rendering:pixelated>'
        '<style>@media(orientation:portrait){#z{object-fit:contain}}</style>'
        '<script>' + js + boot + '</script>')
# document.write + String.fromCharCode path requires pure ASCII
assert all(ord(ch) < 128 for ch in html), "non-ascii byte in game.html"

# deflate-raw (no gzip header/trailer): saves 18 bytes before the double base64
# tax, i.e. ~30 payload bytes.  DecompressionStream('deflate-raw') is in the same
# browser set as 'gzip' (Firefox 113+, Chrome 103+, Safari 16.4+).
co = zlib.compressobj(9, zlib.DEFLATED, -15)
gz = co.compress(html.encode()) + co.flush()
try:
    # Zopfli is a deflate encoder, not a different format, so the browser side
    # (DecompressionStream('deflate-raw')) is unchanged - it just picks better
    # back-references.  Strip zlib's 2-byte header + 4-byte adler32 to get the
    # raw stream.  Measured 21 bytes smaller here (~28 payload bytes after
    # base64 + the escape tax), which is what pays for v10's map generator.
    import zopfli.zlib
    z = zopfli.zlib.compress(html.encode())
    gz2 = z[2:-4]
    assert zlib.decompress(gz2, -15) == html.encode(), "zopfli raw round-trip failed"
    if len(gz2) < len(gz):
        gz = gz2
except ImportError:      # optional: fall back to our own level-9 deflate
    pass
b32blob = b32(gz)
# v13: base64 -> base32.  Two reasons, and only the second one is about bytes:
#  1. the whole base64 alphabet's '+' had to be rewritten to '-' and put back by
#     the wrapper (v10's trick, 19 chars of JS for 65 payload bytes).  Every
#     base32 character is already URI-safe, so that hack is gone.
#  2. base64's lowercase letters are NOT in the QR alphanumeric set, so a base64
#     blob forces the entire payload into byte mode and the 2953-byte ceiling.
#     base32 uses only 0-9 and A-V, so the segment optimizer can move the blob
#     into alphanumeric mode at 5.5 bits/char.  See the module docstring for the
#     measured 2676 -> 3212 chars, 21408 -> 17666 bits.
# document.write from a .then() runs after the parent document closed, which
# orphaned the boot script's canvas binding (proved live: canvas painted 0 px
# though every function was alive). Fix: document.open() swaps in a FRESH live
# document synchronously, then write/close rebuild it - boot script binds to
# the new canvas. Shorter than an iframe+srcdoc too (fits under 2953).
# v11: the bytes come in through new(Response)(bytes).body rather than
# new Blob([bytes]).stream() - same ReadableStream, one space fewer, and no [ ]
# (both of which the data URI must escape as 6-byte %5B/%5D).  new(Response)(x)
# IS new Response(x): the grammar allows a parenthesised MemberExpression after
# new, and writing it that way keeps the space out of the payload.  Node's
# undici Response works identically, which is what a headless wrapper check
# runs this wrapper against.
wrapper = ("<script>s='" + b32blob + "';" + DEC + ";new(Response)(new(Response)("
           "new Uint8Array(u)).body.pipeThrough(new(DecompressionStream)"
           "('deflate-raw'))).text().then(x=>(document.open(),"
           "document.write(x),document.close()))</script>")

# The outer URI is percent-encoded, NOT base64.  v9 measured why: wrapping the
# wrapper in base64 again re-taxed the whole payload at 4/3 (2196 -> 2928 chars),
# but the wrapper is ~90% blob and that alphabet is almost entirely URI-safe, so
# percent-encoding costs 3 bytes only for the characters that really need
# escaping.  A real data:text/html, URI (RFC 2397) - not a data: URL with a
# nonstandard mediatype.  v13: the blob is now 0-9A-V, so the only escapes left
# are the wrapper's own JS punctuation (< > and the '+' in b+=5).
SAFE = "/=._-~()*!$&'@,;"   # base32 alphabet A-Z0-9 + boot punctuation
pct = urllib.parse.quote(wrapper, safe=SAFE)
assert urllib.parse.unquote(pct) == wrapper, "percent round-trip is not lossless"
# (',' and ';' stay raw above: only the mediatype before the FIRST ',' can carry a
# parameter, so they are unambiguous inside the data part and cost no escapes.)
uri = "data:text/html," + pct
# v13: the budget is BITS, not characters.  The payload is now longer as a string
# (3547 chars) and fits anyway, because 3212 of those characters cost 5.5 bits
# instead of 8.  tools/finalize_qr.py is the authority - it builds the symbol
# with fit=False and lets qrcode raise - but this estimate keeps the gate here.
bits = qr_bits(uri)
spare = (CAP_BITS - bits) / 8
print("game.html bytes:", len(html))
print("deflate-raw(html):", len(gz), "wrapper chars:", len(wrapper))
print("dataURI payload:", len(uri), "chars,", bits, "of", CAP_BITS, "bits",
      "FITS" if bits <= CAP_BITS else "OVER by %d bits" % (bits - CAP_BITS),
      "| spare %.0f bytes-equivalent" % spare)
open(os.path.join(ROOT, "game.html"), "w", encoding="utf-8").write(html)
open(os.path.join(ROOT, "build", "payload.txt"), "w", encoding="utf-8").write(uri)
sys.exit(0 if bits <= CAP_BITS else 1)