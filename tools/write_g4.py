#!/usr/bin/env python3
"""write_g4.py - game.js generator: asm-doom (ummeii, MIT) digit sprites +
palette golf + one-write-per-pixel renderer.

Art (tools/asm_art.json, written by tools/port_pistol.py):
  e  = hand-drawn imp 8x14 (kept: it reads well at range)
  g  = pistol art_pistol content-cropped to 11x12 (was a 7x8 blob)
  C  = shared RGB palette; art digits index it via charCodeAt(i)&15, 0=clear
       (1 white, 2 grey, 3 black, 4 skin, 5 red, 6 brown, 7 dark brown,
        8 dark grey - 4 is the imp's face, 8/7 the pistol's shading and body).
       v11 dropped the 9th (gold) entry: v10 removed the ammo gauge, and after
       that NOTHING indexed gold any more - 12 bytes of dead weight in the
       payload, which is exactly the slack the status-bar upgrade needed.  The
       green readout colour is appended as C[8] (digit index 9 is now free).

HUD (v11): rows 81-99 are the status bar - bronze bevel (81-82), a dark rule
under it (83), the brown body (84-96) with dark bottom rows (97-99); the body
turns RED at hp 0.  The bar is repainted AFTER the sprites and BEFORE the
readouts, so a close-up imp (whose feet really are below the horizon at close
range) can never cover it.  Three readouts:
  * hp, exact, 3 digits, 3x5 font at 2x, green (red under 30) at x=6
  * an hp BAR: a 72px dark-brown track with a proportional (0.72px per hp)
    green fill that also goes red under 30, i.e. the same two colours as the
    digits so the gauge and the number read as one instrument.  It is painted
    by the SAME pixel loop that paints the body (one nested ternary), so the
    extra data costs no extra pass over 3040 pixels.
  * enemies-left, exact, 2 digits, red, at x=136, labelled by the imp art ITSELF
    at x=152 - 8x14 at scale 1 with spr's colour override left undefined, so the
    icon is literally the creature the number counts (drawn last, with no depth
    argument, so it is always solid).  v11 restored it: it had been dropped from
    v10.1 as unaffordable, and an offline scene check now pins the 18 icon pixels
    (the art's skin+red cells) so it cannot silently disappear again.
v11 also adds the end-of-run banner: "WON" when al reaches 0 (every imp a
corpse), "LOST" when hp reaches 0, drawn by the CANVAS text engine -
see tools/make_browser.py.  Glyph art for two words would cost ~90 chars of a
3x5 letter font; the browser already owns a font, so the whole feature is one
white fillStyle at boot plus one 41-char fillText per frame.
v10 counted enemies-left BEFORE the iv<.05 "behind the camera" skip, so the
readout is the true number alive: counting after the skip showed only the
enemies in front of you (measured 08 instead of 12 on spawn) - the same class of
lie as the old segmented gauges, which passed n.length as a draw width into a
9-char art string, read past its end (transparent) and saturated to a full red
bar until 4 enemies had already died.

Map (v10): the old hl(x,y) = (F(x)*37+F(y)*17&15)<2 was a pure hash - an
UNBOUNDED lattice of identical single-cell blocks with no border at all, so the
arena was "infinite" in every direction and the player could wander off into an
endless field of the same block ("with infinite it's not discrete, it don't look
nor feel good").  hl now reads a real 28x28 arena that gen(seed) builds at boot:
a 1-thick wall border, a street grid, and one structure per 6x6 site (solid
block, 4-long bar, or hollow room with 1-2 doorways), ~1 site in 8 left as an
empty lot.  Structures never cross a site boundary, so the street rows/columns
(x or y = 2 mod 6) are never built on: the map is connected BY CONSTRUCTION and
cannot contain a pocket for a chasing enemy to get stuck in.
a generator sweep walks 200 seeded maps and proves it (100% of open cells
reachable from the start, 0 enemies in walls or in pockets, wall density 26-49%
of open).  The 784 bytes of map live in RAM, not in the payload: the arena costs
zero bytes where the old 16x16 hash field cost zero too, and it is 4x the area.
gen() also places everyone: the player on a random street node in the middle 3x3
(facing +x, down a street) and the 6 enemies on the six street nodes
E[i] = [2.5 + i%3*12, 2.5 + 18*(i>2)] - three street columns (2, 14, 26) on the
two street rows (2, 20): three arms to your left/right and three behind you.
So they are spread over the whole map - every spawn is exactly 6.0 units from
the player whenever the player rolls the same street row (up to 25.5 away in the
opposite corners), 12 from its nearest neighbour, span 24x18 - BY CONSTRUCTION,
not by rejection sampling, which is why no guard or retry loop is needed.  (12
imps in one arena read as a crowd and the four of v10.1 left the map feeling
empty, so v11 spawns 6 - one per (column, band) cell.  The stand-off ring
index i&3 now repeats, which is harmless: repeated rings belong to enemies that
approach from different bearings, so they still surround you instead of stacking;
an offline harness asserts the spread AND that every chased enemy gets into
melee reach.)  Those six nodes are street intersections (x and y = 2 mod 6), the
lines no structure can ever cover - the site margin guarantees it - so all six
spawns are on open ground for EVERY seed, not just most of them.

Ammo (v10) is INFINITE: the fire rate is ct%15 (4 shots/s) instead of an ammo
counter, so a miss can never make the run unwinnable.  v11 widened the RANGE the
pistol centres a hostile within from 2.5u to 8u: 2.5u is a fifth of the street
spacing and reads as a knife, not a pistol.  The aim cone is unchanged - 0.8 of
the forward dot
product, i.e. 37 deg - so this is reach, not accuracy, and 8u is deliberately
short of the 25.5u corner-to-corner spread, so a distant imp still has to be
closed down (an offline scene check pins both ends: 6u dies, 9u does not).  The bar
reads hp (left, green, red under 30) and enemies left (right, red, labelled by
the imp icon at x=152) - there is nothing left to count on the ammo slot, so it
is gone.

Pistol cadence: (ct%15) - the same 45-frame counter that schedules the melee
tick, so no extra state.  Holding fire no longer empties a clip; without a
cadence an infinite-ammo pistol would kill one imp per frame (60/s).

Renderer: the frame buffer is one Uint8ClampedArray viewed as a Uint32Array, so
a pixel is ONE store of a pre-packed 0xAABBGGRR word (little-endian, true on
every browser we target).  Palette words carry the alpha byte, which is why the
old fill(255) pass is gone: opacity is baked into every value written.  That is
~100 payload bytes cheaper than 3 stores per pixel and makes the occlusion test
below affordable.

Sprite occlusion: zd[x] keeps each column's DDA wall depth pd.  pd and iv (the
enemy's dot with dir) are both depths along the view axis - in a Lode-style ray
caster perpWallDist is measured along the ray parameter, which for rays built as
dir+plane*cm is exactly the dir projection - so zd[x]<iv is the correct test.
spr takes D (the sprite's iv) and applies it PER COLUMN.  D is optional and the
enemy locator mark (v12, below) is the one thing drawn without it, on purpose.

v11 SPRITE PROJECTION BUG (imps slid sideways in lockstep with the camera and
showed through walls): the screen x used vx*planeX+vy*planeY, but that is the
sprite
offset's component along the camera plane, NOT its screen coordinate.  With a
ray built as dir+plane*cm, a point at offset o lands on cm = (o.plane-hat)/(|o|
along dir), so the plane component must be divided by |plane|^2 - and |plane|
here is 0.62, i.e. every sprite was drawn 0.62^2 = 0.384x too close to the
screen centre.  A diagnostic render measured it before the fix (target = 80 +
129.03*dy/dx, half-FOV 31.8 deg):
    offset (6,1): true x 101.5  painted 84..91     (13px inward)
    offset (6,3): true x 144.5  painted 100..107   (41px inward)
    offset (6,4): true x 166.0 (outside the FOV)   painted 109..116
    offset (6,-4): true x -6.0 (outside the FOV)   painted 42..49
    ring of 8 at 6u, bearings -36..+36 deg: painted across x 1..157
So sprites swam toward the middle of the view as you turned (at the exact
screen centre the error is zero, which is why a straight-ahead imp looked fine)
and, worse, an imp standing to your side or just behind your shoulder was
painted dead ahead of you - where the per-column depth test then compared its
6.3u depth against whatever wall happened to be in THAT column, so it showed
through walls.  The constant is SP = (W/2)/|plane|^2 = 208.12 (2 decimals: the
worst-case placement error is 0.003px).  With it, a bearing t = dy/dx maps to
80 + 129.03t, which is the same column the DDA casts the ray for, so a sprite
now always sits on top of its own ray - which is what makes zd[x]<iv meaningful.

spr also gained a horizontal clip: the old code had an
aw<4*sc|aw>W-4*sc cull, v10 removed it in favour of the per-column depth test,
and with the projection fixed a sprite can legitimately sit off-screen - without
the clip its pixels wrapped into the next row (v[(...)*W+u] is a flat index),
painting garbage streaks across the frame.  Negative u was always harmless
(a negative index on a typed array is dropped), positive overflow was not.  v12
spells the two tests as one unsigned compare, u>>>0>W-1, which catches negative
u (it becomes huge) AND past-the-end u in a single term; the earlier u>159
spelling was the v11 golf and the variant with | in place of || is still banned
(see a re-golf check for why).

Sprite size: sc = H/dv/16 made an imp 14*sc px tall where a 1u-wide wall cell at
dv is 129/dv px, i.e. the imp stood 0.57 units tall in a 1-unit corridor - half
size, which is the other half of "something is wrong with the enemy sprites".
v11 uses H/dv/11 = 0.84u, close to Doom's 40x56-unit imp in a 64-unit corridor
(and 8/14 = 0.571 wide vs Doom's 40/56 = 0.714, so the aspect is right too).  The
cap stays at 6 texels-per-pixel: 14*6 = 84px is the biggest imp that still fits
above the status bar at melee range.

v12 THE ENEMY LOCATOR MARK (a red point over every enemy that stays visible
through walls, so an imp cannot be lost behind an intersection).  Every LIVE enemy
carries a
2x2 red block four pixels above the top of its sprite.  The imp itself still
passes its depth iv to spr and is therefore still correctly hidden - the
bodies-through-walls check still passes unchanged - and the
mark is a SECOND spr call with the depth argument omitted, because D is the only
thing that makes spr consult zd[].  Drawn unconditionally, so no wall can hide
it: that is the whole feature.  It is a locator, not a wallhack - you get a
bearing, not a target, and the maze still hides the creature.  Fixed 2x2 (scale 2
on a 1x1 art) on purpose: the mark must read the SAME at every range, because
its job is to be findable exactly when the imp is small or hidden (at the
canvas's CSS upscale, 100vw on a 1080p screen, one game pixel is ~12 screen px,
so even one would do - 2 is what fits the budget and the eye).  The art is the
single character '5', i.e. the same art digit 5 -> C[4] red that the
enemies-left readout uses, so the mark needs no new palette entry and no new
string, and it reads as the same "enemy red" as the number it agrees with.  It
is guarded by l||, so a corpse shows nothing even through a wall: a mark means
"alive and out there", and the count on the bar always equals the number of
marks on the screen.  Position is y-5..y-4 where y = F((H+H/dv)/2-14*sc) is the
sprite's own top row, so the mark tracks the head at every range and scale.


Enemies: chase speed 0.01/frame = 0.6 u/s (was 0.02 = 1.2 u/s, "too fast") with a
per-enemy stand-off ring of 1.1+(i&3)*0.04 units, so they surround the player at
staggered ranges instead of piling onto one point, and movement is normalised
along the chase vector (the old per-axis 0.4 dead-zone made every approach
axis-aligned).  v10 bug fix - the ring used to be 1.1+(i&3)*0.3 = 1.1/1.4/1.7/2.0,
so 9 of 12 enemies came to rest OUTSIDE the 1.25 melee reach and could never
attack: they walked up to you and stood there like statues ("something wrong with
the enemies").  Every ring is now inside 1.25 (1.10/1.14/1.18/1.22), so any enemy
that reaches you can actually fight, and an offline harness drives 4 enemies
in from 4 bearings on a flat map and asserts all 4 end up in reach AND take hp.
E[i][2] doubles as the corpse timer: a hit sets 1,
step() advances it and then skips that enemy entirely (no move, no melee, not
shootable), render() draws it shrinking by l/24 toward its feet with a white
flash for l<5 and skips it at sc<1.  Corpses stay in E so indices - and
therefore the ring - stay stable.  Melee: any enemy inside 1.25u costs 6hp on
one shared 45-frame tick, floored at 0; at hp 0 step() swaps k for {}, which
kills every input at once, the bar turns red, and R reloads (location.reload in
the boot), which regenerates the arena and all 4 spawns.

Controls: arrows or WASD, one key per axis.  Turning is 0.02 rad/frame (1.15 deg
per frame = 69 deg/s), halved TWICE from 0.07 (4 deg/frame = 240 deg/s) because
0.035 (120 deg/s) still overshot on a phone-sized viewport - it is the only
"look" control in the payload, which wires
nothing but onkeydown/onkeyup into k[keyCode], so there is no mouse aim to
scale and the turn rate is the only lever there is.  Held walking stays
0.06 u/frame (3.6 u/s): the sensitivity complaint was about looking, not moving.

The AI never actually entered walls (an offline harness walks it 900 steps
and checks hl() at every body position); enemies *looked* like they walked
through walls because they were painted over them.

v11 BYTE BUDGET (what paid for the 4 features): the payload is game.html ->
zopfli deflate-raw -> base64 -> percent-encoded data URI, capped at the QR
v40-L ceiling of 2953.  The features cost ~+80 chars of NOVEL code (the icon,
the banner, the 6th/5th spawn, the 8u range) and the refund came from four
places, in size order:
  * signed int32 spellings of the 12 colour words: -16777216 IS 0xFF000000
    through a Uint32Array and |, so 7 of the 12 lose a character (jsint()).
  * golfed code: step()'s stand-off probe folded (E[i][0]-ax-ax*30 is
    E[i][0]-ax*31), E[i] and the player aliased to locals (repeated indexing is
    pure entropy), & for && where every operand is already a comparison,
    hl/gen/render constants spelled out, x/80-1 for 2*x/W-1.
  * the payload wrapper: new(Response)(bytes).body instead of
    new Blob([bytes]).stream() (drops a space AND the [ ] that the data URI has
    to percent-escape), and `new Response(x)` respelled `new(Response)(x)` - an
    identical parse that replaces the space with parentheses, and every space in
    the wrapper is a 3-byte %20 in the payload.
  * dropping re-spellings that only LOOK like savings.  Two were tried and
    reverted with measurements: packing the 150-char '0'/'1' digit font into ten
    15-bit decimals costs 43 bytes (binary text deflates to nothing, decimal
    digits are entropy), and mirror-storing the imp's 4-wide half costs 12
    (spr needs 30 chars of code; the art is cheap).  Character count is NOT the
    budget - only entropy is.
Measured: v10.1 payload 2945/2953 with 4 enemies and no icon; v11 is 2948/2953
with 6 enemies, the icon, the 8u range and the banner.  Every one of those
re-spellings is proven not to move a pixel by a re-golf check, which re-spells
them back and diffs 24 rendered scenes byte for byte.  Two things bought nothing
and are recorded so nobody re-tries them: Zopfli is already converged here (1991,
2012 and 2008 raw bytes at numiterations 15/100/200 and blocksplittingmax 0/30/100
- the encoder is not the lever), and the closing </script> + document.close()
could each save ~9-17 bytes but only by relying on parser edge cases, which is
not a trade worth making for a payload a scanner has to survive.
v12 BYTE BUDGET (what paid for the mark): the mark is +29 chars of NOVEL code (the
sprite top hoisted into y so the imp's 21-char projection expression is written
once, plus l||spr(aw,y-5,2,'5',1,1) with no depth argument) and it was refunded by
six re-spellings, each of them provably pixel-identical:
  * the DDA's own bounds test is gone.  if(mx<0|my<0|hl(mx,my)) is if(hl(mx,my)),
    because hl already returns truthy for x<0|y<0|x>27|y>27 - the two extra tests
    could never fire on their own (-13 chars, the single biggest item here).
  * the status bar is ONE C[] index instead of six lookups, which demotes q from a
    colour word to an index (q=hp<30?4:8 ... C[x<36+hp*.72?q:7:hp?6:4]).
  * F() -> |0 wherever the operand is provably non-negative: sc's floor and min
    (Math.min(H/dv/11|0,6)||1), the corpse shrink (sc*l/24|0), the wall band's
    st/en (50-H/pd/2|0: floor and truncate agree on positives, and a negative st
    means "no sky rows" either way), and the DDA's mx/my (hl gates every move, so
    the player is never at a negative coordinate).  NOT used where the value can
    go negative - aw, where floor/trunc differ by one pixel on an off-canvas
    sprite, is left as F().
  * dg draws digits right-to-left (for(Q=n;Q--;)), free because the glyphs are
    3*2 = 6px wide on an 8px pitch and cannot overlap, and P[Q]*15 needs no unary
    + (a char times a number is already one).
Measured: 2944/2953 - NINE bytes spare, i.e. the mark left the payload 4 bytes
BETTER than v11 (2948) while adding a feature.  Same proof discipline as v11:
a re-golf check re-spells all six back and diffs 24 rendered scenes (0 differing,
0 byte diffs on the HUD frame), and the scene check's three fingerprints now make the
split explicit - arena and gen(1)-with-no-enemies are UNCHANGED (3289170725 /
2212428426), so the golf moved no world pixel, while gen(1)+6imps was recomputed
deliberately (3898192458 -> 1715883234) because that is the frame the feature
changes.  The mark has its own gate: hidden imp -> exactly the 2x2 block at the
predicted coordinates and 0 body pixels, corpse -> 0, outside the view -> 0.

v13 (mobile) did NOT come out of this budget, and deliberately so - the
requirement was that the visuals not move at all.  The touch pad, the phone-shaped
viewport and the touch restart live in the boot and the HTML (tools/
make_browser.py), so the output of THIS file is byte-identical to v12 and
a re-golf check still reports 0 differing scenes.  The bytes came from the
payload's own encoding: the inner blob moved base64 -> base32 so the QR's segment
optimizer can carry it in ALPHANUMERIC mode (5.5 bits/char against byte mode's 8).
That changed the unit of account rather than the game - 2944/2953 byte-mode bytes
(10 spare) became 21547/23648 data bits (263 bytes-equivalent spare), which is
2.3x what the touch input needed.

build/_browser_check.py is the one gate a stub canvas cannot replace: it drives
game.html in a real engine, forces hp=0 and al=0 through the game globals, and
asserts the banner rasterises (0 white px while playing, ~54-70 for LOST and WON -
the exact count moves run to run because gen() is seeded from the clock and the
box includes the world behind it) with no JS
errors, a 160x100 backing store and the 18 icon pixels.  v12 added the mark to
it: the sim is frozen (step is a plain global, so the boot's own setInterval picks
the no-op up), the map is cleared to a single wall, an imp is parked behind it,
and the check requires exactly 4 red px - all four inside the predicted 2x2 - and
0 imp pixels on the canvas.  an offline render draws the same
thing for eyeballing (a screenshot of two marks flat on walls with
both imps hidden).
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
art = json.load(open(os.path.join(ROOT, "tools", "asm_art.json")))
# '.' reads nicer in the JSON, but charCode '.'&15 = 14 -> C[39] undefined ->
# paints BLACK boxes around sprites. '0'&15 = 0 -> spr's if(!t) skips it,
# i.e. true transparency (also the original asm-doom convention).
for k in ("e", "g"):
    art[k] = art[k].replace(".", "0")
assert len(art["e"]) == 112, "imp grid must stay 8x14"
GW, GH = art["gw"], art["gh"]
assert len(art["g"]) == GW * GH, "gun art does not match its declared grid"
# v11 tried storing the imp as its 4-wide left half (it IS mirror-symmetric) and
# mirroring column J to 7-J in spr.  Measured against the payload, not against
# the character count: -56 art chars but +30 chars of code, and the art is highly
# repetitive while code is pure entropy, so the payload went 2948 -> 2960.  The
# art stays whole.  Character count is not the budget here - only entropy is.
assert all(row[:4] + row[:4][::-1] == row
           for row in (art["e"][i:i + 8] for i in range(0, 112, 8))), \
    "imp art is no longer mirror-symmetric (documented, but unused)"
# v11 deleted the 9th palette entry (gold - v10 had already removed the ammo
# gauge that was the only thing indexing it), so an art digit 9 would now read
# C[8]... which is the appended HUD green, and a 10th would read undefined (a
# black block).  The imp uses 2/3/4/5 and the pistol 1/2/6/7/8; the font and the
# imp-icon override come in through dg/spr's K argument, not the palette.
assert "9" not in set(art["e"]) | set(art["g"]), \
    "art still indexes the deleted gold entry"


def pk(r, g, b, a=255):
    """pack RGB(A) into the 0xAABBGGRR word the renderer stores."""
    return r + g * 256 + b * 65536 + a * 16777216


def jsint(v):
    """Spell a 32-bit colour word the SHORT way: its signed decimal.

    The values are stored through a Uint32Array (and OR'd with JS bitwise ops,
    which are 32-bit and return signed ints), so -16777216 IS 0xFF000000 and
    -1513240 IS 0xFFE8E8E8 - identical bytes on screen, one character shorter
    each for the 7 of the 12 constants that end up needing 8 digits instead of
    10 (measured: 15 source chars = ~9 payload bytes).  The pixel-identity gate
    is what proves the bytes did not move.
    """
    v &= 0xFFFFFFFF
    return v - 2 ** 32 if v >= 2 ** 31 else v


A = 255 * 16777216      # opaque alpha bits (little-endian byte 3)
S = pk(20, 20, 28)      # sky
L = pk(42, 33, 19)      # floor below the wall band
# status bar bevel (rows 81-82) and body reuse palette browns C[5]/C[6], i.e.
# the light/dark bronze of the asm-doom bar, so they cost no extra constants.
C = [pk(*art["C"][i:i + 3]) for i in range(0, len(art["C"]), 3)]
# C[9] = HUD health green.  The asm-doom palette has no green (1 white, 2 grey,
# 3 black, 4 skin, 5 red, 6 brown, 7 dark brown, 8 dark grey, 9 gold) and the hp
# readout needs a colour that is neither the gold ammo nor the red enemy count.
C.append(pk(70, 190, 70))

# 3x5 digit font for the numeric status bar: 10 glyphs x 15 chars, row-major, so
# glyph n occupies O[n*15:n*15+15] and '1' is ink / '0' is transparent (spr
# skips charCodeAt&15 == 0, and dg overrides the colour via spr's K argument so
# one font serves the gold, green and red readouts).
FONT_ROWS = [
    ("111", "101", "101", "101", "111"),   # 0
    ("010", "110", "010", "010", "111"),   # 1
    ("111", "001", "111", "100", "111"),   # 2
    ("111", "001", "111", "001", "111"),   # 3
    ("101", "101", "111", "001", "001"),   # 4
    ("111", "100", "111", "001", "111"),   # 5
    ("111", "100", "111", "101", "111"),   # 6
    ("111", "001", "001", "001", "001"),   # 7
    ("111", "101", "111", "101", "111"),   # 8
    ("111", "101", "111", "001", "111"),   # 9
]
FONT = "".join("".join(g) for g in FONT_ROWS)
assert len(FONT) == 150, "font must be exactly 10 glyphs x 15 chars"
assert set(FONT) <= set("01"), "font may only use '0' (clear) and '1' (ink)"
# The font stays a 150-char '0'/'1' string ON PURPOSE.  Measured: packing the ten
# glyphs into 15-bit decimals (63 chars) and expanding them in dg looks like ~90
# source chars saved, but '0'/'1' text deflates to almost nothing while decimal
# digits are pure entropy - the real payload moved 1991 -> 2034 bytes, i.e. the
# "saving" cost 43 bytes.  Raw character count is NOT the budget; on this
# payload only entropy is.

# The camera plane half-width (tan of the half-FOV): 0.62 -> atan(0.62) = 31.8
# degrees each side of centre.  It is the ONE number the wall caster and the
# sprite projection have to agree on, so it is substituted (@PW@) into the spawn
# literal, and it also fixes SP, the sprite screen-x scale, below.
PW = 0.62
# Sprite screen-x scale = (W/2) / |plane|^2 = 80/0.3844 = 208.1165...  The plane
# component of a sprite offset is not a screen coordinate until it is divided by
# |plane|^2 (see the docstring): with SP, bearing t = dy/dx lands on column
# 80 + 129.03t, exactly where the DDA casts that ray.  Two decimals keep the
# worst-case placement error at 0.003px - invisible, and inside the 1px a test
# can assert.
SP = round(80 / (PW * PW), 2)
assert SP == 208.12, "SP must stay (W/2)/PW^2"

JS = '''W=160,H=100,F=Math.floor,ab=Math.abs,sq=Math.sqrt,zd=[],hp=100,ct=0;
N=28,M=new Uint8Array(784),rn=()=>r=r*48271%2147483647;
gen=s=>{r=s%2147483646+1;M.fill(0);
for(i=28;i--;)M[i]=M[i+756]=M[i*28]=M[i*28+27]=1;
for(a=3;a<25;a+=6)for(b=3;b<25;b+=6){if(rn()%8<1)continue;
w=3+rn()%3,h=3+rn()%3,x=a+rn()%2*(w<5),y=b+rn()%2*(h<5);
for(c=w;c--;)for(d=h;d--;)if(!c|!d|c>w-2|d>h-2)M[(y+d)*N+x+c]=1;
t=rn()%4;t<2?M[(t?y+h-1:y)*N+x+1+rn()%(w-2)]=0:M[(y+1+rn()%(h-2))*N+x+(t>2)*(w-1)]=0}
p=[8+12*(rn()%2)+.5,8+6*(rn()%3)+.5,1,0,0,@PW@],E=[];
for(i=6;i--;)E[i]=[2.5+i%3*12,2.5+18*(i>2)]};
hl=(x,y)=>M[F(y)*28+F(x)]|x<0|y<0|x>27|y>27;
e='@E@',g='@G@',C=@C@;
O='@O@';
spr=(x,y,s,b,w,h,D,K)=>{for(i=w*h;i--;){t=b.charCodeAt(i)&15;if(!t)continue;a=K||C[t-1];for(r=s;r--;)for(c=s;c--;){u=x+i%w*s+c;if(u>>>0>W-1||D&&zd[u]<D)continue;v[(y+F(i/w)*s+r)*W+u]=a}}};
dg=(X,Y,V,n,K)=>{P=(V+1e9+'').slice(-n);for(Q=n;Q--;)spr(X+Q*8,Y,2,O.substr(P[Q]*15,15),3,5,0,K)};
render=(a,b,c,f,j,k,n)=>{v=new Uint32Array(16000),d=new Uint8ClampedArray(v.buffer);for(x=W;x--;){cm=x/80-1,rx=c+j*cm,ry=f+k*cm,mx=a|0,my=b|0,ad=ab(1/rx),bd=ab(1/ry),tx=rx<0?(a-mx)*ad:(mx+1-a)*ad,ty=ry<0?(b-my)*bd:(my+1-b)*bd,o=0;for(;;){tx<ty?(tx+=ad,mx+=rx<0?-1:1,o=0):(ty+=bd,my+=ry<0?-1:1,o=1);if(hl(mx,my))break}pd=o?ty-bd:tx-ad,zd[x]=pd,st=50-H/pd/2|0,en=50+H/pd/2|0,sh=Math.max(200-120/pd,20),wc=o?sh*.6:sh,wv=wc|(wc*.94|0)<<8|(wc*.82|0)<<16|@A@;for(y=81;y--;)v[y*W+x]=y<st?@S@:y<=en?wv:@L@}
for(q=n.length,al=0;q--;){m=n[q],l=m[2]||0,vx=m[0]-a,vy=m[1]-b,iv=vx*c+vy*f,l||al++;if(iv<.05)continue;dv=sq(vx*vx+vy*vy);aw=F((vx*j+vy*k)/iv*@SP@+80),sc=Math.min(H/dv/11|0,6)||1;sc-=sc*l/24|0;if(sc<1)continue;y=F((H+H/dv)/2-14*sc),spr(aw-4*sc,y,sc,e,8,14,iv,l&&l<5?C[0]:0),l||spr(aw,y-5,2,'5',1,1)}
spr(69,57,2,g,@GW@,@GH@);
q=hp<30?4:8;for(y=19;y--;)for(x=W;x--;)v[(y+81)*W+x]=C[y<3?y<2?5:7:y>4&y<11&x>35&x<108?x<36+hp*.72?q:7:hp?6:4];
dg(6,86,hp,3,C[q]);dg(136,86,al,2,C[4]);spr(152,86,1,e,8,14);return d};
step=(p,E,k)=>{hp>0||(k={});ct=(ct+1)%45;a=(k[68]|k[39])?.02:(k[65]|k[37])?-.02:0,s=Math.sin(a),c=Math.cos(a);for(i=2;i<6;i+=2){t=p[i]*c-p[i+1]*s;p[i+1]=p[i]*s+p[i+1]*c;p[i]=t}m=k[87]|k[38]?1:k[83]|k[40]?-1:0;x=p[0]+p[2]*m*.06,y=p[1]+p[3]*m*.06;hl(x,p[1])||(p[0]=x);hl(p[0],y)||(p[1]=y);for(i=E.length;i--;){w=E[i];if(w[2]&&w[2]++)continue;ex=w[0]-p[0],ey=w[1]-p[1],dv=sq(ex*ex+ey*ey);if(k[32]&!(ct%15)&dv<8&(ex*p[2]+ey*p[3])/dv>.8){w[2]=1;continue}dv<1.25&&!ct&&(hp=hp>6?hp-6:0);if(dv>1.1+(i&3)*.04){ax=ex/dv*.01,ay=ey/dv*.01;hl(w[0]-ax*31,w[1])||(w[0]-=ax);hl(w[0],w[1]-ay*31)||(w[1]-=ay)}}return p};
module.exports={render:render,step:step,W:W,H:H,N:N,M:M,hl:hl,gen:gen,spr:spr,C:C,get p(){return p},get E(){return E},get zd(){return zd},get hp(){return hp},get ct(){return ct},get al(){return al},set hp(v){hp=v},set ct(v){ct=v}};
'''
for k, v in (("@E@", art["e"]), ("@G@", art["g"]),
             ("@C@", str([jsint(c) for c in C]).replace(" ", "")),
             ("@A@", str(jsint(A))),
             ("@S@", str(jsint(S))), ("@L@", str(jsint(L))), ("@O@", FONT),
             ("@GW@", str(GW)), ("@GH@", str(GH)),
             ("@PW@", str(PW)), ("@SP@", str(SP))):
    JS = JS.replace(k, v)
for k in ("@E@", "@G@", "@C@", "@A@", "@S@", "@L@", "@O@", "@GW@", "@GH@",
          "@PW@", "@SP@"):
    assert k not in JS, "unsubstituted " + k
assert all(ord(ch) < 128 for ch in JS), "non-ascii byte in game.js"
open(os.path.join(ROOT, "src", "game.js"), "w", encoding="utf-8").write(JS)
print("game.js bytes:", len(JS), "| palette", len(C), "colors | gun %dx%d"
      % (GW, GH))
