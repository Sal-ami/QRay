"""lzss.py - minimal LZSS encoder/decoder (SPEC 3.5 format).
Format: token stream; every 8 tokens one control byte (MSB first).
  flag=1 literal byte | flag=0 match token 2B: hi=(len-3)<<4|off>>8, lo=off&ff.
 final control byte padded with 1s (decoder stops at expected length).
Usage:  lzss.py compress <in> <out> | decompress <in> <out> <rawlen> | selftest
"""
import sys, os

WINDOW = 4096


def compress(data):
    n = len(data)
    out = bytearray()
    heads = {}
    ctl_pos = None
    grp = 0
    i = 0
    while i < n:
        if grp == 0:
            out.append(0)          # control byte placeholder
            ctl_pos = len(out) - 1
        best_len = 0
        best_off = 0
        if i + 3 <= n:
            key = bytes(data[i:i + 3])
            for j in heads.get(key, ()):
                off = i - j
                if off < 1 or off >= WINDOW:
                    continue
                e = i + 3
                hi = n if n < i + 18 else i + 18
                while e < hi and data[e] == data[j + e - i]:
                    e += 1
                if e - i > best_len:
                    best_len, best_off = e - i, off
        if best_len >= 3:
            out.append(((best_len - 3) << 4) | (best_off >> 8))
            out.append(best_off & 0xFF)
            for k in range(i, i + best_len):
                if k + 3 <= n:
                    heads.setdefault(bytes(data[k:k + 3]), []).append(k)
            i += best_len
        else:
            out.append(data[i])
            out[ctl_pos] |= 1 << (7 - grp)
            if i + 3 <= n:
                heads.setdefault(bytes(data[i:i + 3]), []).append(i)
            i += 1
        grp += 1
        if grp == 8:
            grp = 0
            ctl_pos = None
    # pad final control byte's UNUSED low bits with 1s
    if ctl_pos is not None:
        out[ctl_pos] |= (1 << (8 - grp)) - 1
    return bytes(out)


def decompress(data, out_len):
    out = bytearray()
    i = 0
    n = len(data)
    flax = 0
    bits = 0
    while len(out) < out_len and i < n:
        if bits == 0:
            flax = data[i]; i += 1; bits = 8
        if flax & 0x80:
            out.append(data[i]); i += 1
        else:
            hi, lo = data[i], data[i + 1]; i += 2
            ln = (hi >> 4) + 3
            off = ((hi & 0xF) << 8) | lo
            if off == 0:
                off = 1
            start = len(out) - off
            for k in range(ln):
                out.append(out[start + k])
        flax = (flax << 1) & 0xFF
        bits -= 1
    return bytes(out)


def main():
    if sys.argv[1] == "compress":
        open(sys.argv[3], "wb").write(compress(open(sys.argv[2], "rb").read()))
    elif sys.argv[1] == "decompress":
        open(sys.argv[3], "wb").write(decompress(open(sys.argv[2], "rb").read(), int(sys.argv[4])))
    elif sys.argv[1] == "selftest":
        d = open(__file__, "rb").read()
        c = compress(d)
        dd = decompress(c, len(d))
        assert dd == d, "ROUND-TRIP FAILED"
        print(f"selftest OK: {len(d)} -> {len(c)} bytes ({100 * len(c) / len(d):.1f}%)")


if __name__ == "__main__":
    main()