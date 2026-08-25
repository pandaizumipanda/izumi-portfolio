# -*- coding: utf-8 -*-
"""
散りばめ装飾（images/deco/）の表示サイズに合わせた縮小版をつくる

    python3 tools/shrink_deco.py           新しい・更新された画像だけ処理
    python3 tools/shrink_deco.py --force   すべて作り直す

images/deco/ の画像を images/deco-sm/ へ書き出します。
  1. 長辺 360px に縮小（macOS 標準の sips を使用）
  2. 透明な余白を切り落として正方形に収め直す
     （元画像は絵のまわりに余白が多く、そのままだと小さく見えるため）

サイトは deco-sm/ があればそちらを読み込みます。元画像はそのままです。
"""

import os
import struct
import subprocess
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "images", "deco")
OUT_DIR = os.path.join(ROOT, "images", "deco-sm")
MAX_PX = 360
MARGIN = 0.04          # 切り出しの外側に少しだけ余白を残す
EXTS = (".png", ".jpg", ".jpeg")


# ------------------------------------------------------------------ PNG
def read_png(path):
    """RGBA(8bit, 非インターレース)のPNGを読み込む"""
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, idat, w, h, ct = 8, b"", None, None, None
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, bd, ct, cm, fm, il = struct.unpack(">IIBBBBB", data)
            if bd != 8 or ct != 6 or il != 0:
                return None
        elif tag == b"IDAT":
            idat += data
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 4
    buf, prev, i = bytearray(), bytearray(stride), 0
    for _y in range(h):
        f = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        buf += line
        prev = line
    return w, h, buf


def write_png(path, w, h, buf):
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        head = struct.pack(">I", len(data)) + tag + data
        return head + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def trim_square(path):
    """透明な余白を切り落として、絵が中央にくる正方形に収め直す"""
    img = read_png(path)
    if not img:
        return None
    w, h, buf = img
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = buf[y * w * 4:(y + 1) * w * 4]
        for x in range(w):
            if row[x * 4 + 3] > 8:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    if x1 < 0:
        return None
    side = max(x1 - x0 + 1, y1 - y0 + 1)
    side = int(side * (1 + MARGIN * 2))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    out = bytearray(side * side * 4)
    for y in range(side):
        sy = cy - side // 2 + y
        if sy < 0 or sy >= h:
            continue
        for x in range(side):
            sx = cx - side // 2 + x
            if sx < 0 or sx >= w:
                continue
            si, di = (sy * w + sx) * 4, (y * side + x) * 4
            out[di:di + 4] = buf[si:si + 4]
    write_png(path, side, side, out)
    return side


def main():
    force = "--force" in sys.argv
    if not os.path.isdir(SRC_DIR):
        if os.path.isdir(OUT_DIR):
            raise SystemExit(u"images/deco/（元画像）がありません。"
                             u"images/deco-sm/ の縮小版をそのまま使います。")
        raise SystemExit(u"images/deco/ がありません")
    if not os.path.exists("/usr/bin/sips"):
        raise SystemExit(u"sips が見つかりません（macOS 以外では手動で縮小してください）")

    os.makedirs(OUT_DIR, exist_ok=True)
    names = [n for n in sorted(os.listdir(SRC_DIR)) if n.lower().endswith(EXTS)]
    made = skipped = 0
    for n in names:
        src = os.path.join(SRC_DIR, n)
        out = os.path.join(OUT_DIR, n)
        if not force and os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
            skipped += 1
            continue
        subprocess.check_call(["/usr/bin/sips", "-Z", str(MAX_PX), src, "--out", out],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        side = trim_square(out)
        made += 1
        print(u"%-30s %7.1fKB -> %5.1fKB  %s"
              % (n, os.path.getsize(src) / 1024.0, os.path.getsize(out) / 1024.0,
                 (u"%dx%d" % (side, side)) if side else u"(切り出しなし)"))

    removed = 0
    for n in sorted(os.listdir(OUT_DIR)):
        if n.lower().endswith(EXTS) and n not in names:
            os.remove(os.path.join(OUT_DIR, n))
            removed += 1

    print(u"\n%d generated / %d skipped / %d removed  ->  images/deco-sm/"
          % (made, skipped, removed))


if __name__ == "__main__":
    main()
