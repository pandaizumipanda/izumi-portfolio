# -*- coding: utf-8 -*-
"""
プレースホルダーPNG生成スクリプト（標準ライブラリのみ / Pillow不要）

    python tools/gen_placeholders.py            既存ファイルは残して不足分だけ生成
    python tools/gen_placeholders.py --force    すべて再生成（差し替え済み画像も上書き）
    python tools/gen_placeholders.py --list     画像一覧（ファイル名・サイズ・用途）を表示

IMAGES に定義したファイル名・サイズでダミーPNGを images/ に書き出します。
本番画像は「同じファイル名・同じ縦横比」のPNGで上書きすれば差し替え完了です。
"""

import os
import sys
import zlib
import struct
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font5x7 import glyph_rows, text_size, GLYPH_W, GLYPH_H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "images")

# ---------------------------------------------------------------- palette
# サイトのオレンジ基調に合わせた淡色。順番に循環して使用します。
TINTS = [
    ((253, 234, 219), (240, 176, 122), (140, 66, 16)),
    ((255, 240, 226), (245, 194, 140), (150, 78, 22)),
    ((252, 230, 214), (236, 166, 116), (128, 58, 14)),
    ((253, 240, 216), (238, 198, 124), (132, 86, 16)),
    ((250, 228, 222), (232, 168, 148), (128, 60, 40)),
    ((248, 238, 216), (222, 196, 136), (112, 84, 24)),
]


class Canvas:
    def __init__(self, w, h, bg=(255, 255, 255, 255)):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 4)
        row = bytes(bg) * w
        for y in range(h):
            self.buf[y * w * 4:(y + 1) * w * 4] = row

    def px(self, x, y, color, alpha=255):
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 4
        if alpha >= 255:
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]
            self.buf[i + 3] = 255
            return
        if alpha <= 0:
            return
        a = alpha / 255.0
        for k in range(3):
            self.buf[i + k] = int(self.buf[i + k] * (1 - a) + color[k] * a)
        if self.buf[i + 3] < 255:
            self.buf[i + 3] = min(255, int(self.buf[i + 3] + alpha))

    def rect(self, x0, y0, x1, y1, color, alpha=255):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.px(x, y, color, alpha)

    def frame(self, x0, y0, x1, y1, color, t=2, alpha=255):
        self.rect(x0, y0, x1, y0 + t, color, alpha)
        self.rect(x0, y1 - t, x1, y1, color, alpha)
        self.rect(x0, y0, x0 + t, y1, color, alpha)
        self.rect(x1 - t, y0, x1, y1, color, alpha)

    def disc(self, cx, cy, r, color, alpha=255):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                d = math.hypot(x - cx, y - cy)
                if d <= r - 1:
                    self.px(x, y, color, alpha)
                elif d <= r:
                    self.px(x, y, color, int(alpha * (r - d)))

    def hatch(self, color, gap=26, t=3, alpha=255):
        """右下がりの斜線パターン"""
        for k in range(-self.h, self.w + self.h, gap):
            for y in range(self.h):
                for o in range(t):
                    self.px(k + y + o, y, color, alpha)

    def text(self, text, x, y, color, scale=2, tracking=1, alpha=255):
        cx = int(x)
        y = int(y)
        for ch in text:
            rows = glyph_rows(ch)
            for ry in range(GLYPH_H):
                row = rows[ry]
                for rx in range(GLYPH_W):
                    if row[rx] == "1":
                        self.rect(cx + rx * scale, y + ry * scale,
                                  cx + (rx + 1) * scale, y + (ry + 1) * scale,
                                  color, alpha)
            cx += (GLYPH_W + tracking) * scale

    def text_center(self, text, cy, color, scale=2, tracking=1, alpha=255):
        w, h = text_size(text, scale, tracking)
        self.text(text, (self.w - w) // 2, cy - h // 2, color,
                  scale, tracking, alpha)

    def write(self, path):
        raw = bytearray()
        stride = self.w * 4
        for y in range(self.h):
            raw.append(0)
            raw += self.buf[y * stride:(y + 1) * stride]

        def chunk(tag, data):
            head = struct.pack(">I", len(data)) + tag + data
            return head + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        png += chunk(b"IEND", b"")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(png)


# ---------------------------------------------------------------- styles
def draw_photo(cv, label, idx):
    """写真・イラスト枠のプレースホルダー"""
    base, mid, ink = TINTS[idx % len(TINTS)]
    cv.rect(0, 0, cv.w, cv.h, base)
    cv.hatch(mid, gap=max(18, cv.w // 22), t=max(2, cv.w // 320), alpha=55)

    # 中央のソフトな塊（イラストのシルエット代わり）
    r = min(cv.w, cv.h) * 0.30
    cv.disc(cv.w / 2, cv.h * 0.42, r, mid, alpha=110)
    cv.disc(cv.w / 2 - r * 0.62, cv.h * 0.42 - r * 0.74, r * 0.30, mid, alpha=150)
    cv.disc(cv.w / 2 + r * 0.62, cv.h * 0.42 - r * 0.74, r * 0.30, mid, alpha=150)

    # 外枠とコーナートンボ
    pad = max(10, min(cv.w, cv.h) // 24)
    t = max(2, min(cv.w, cv.h) // 280)
    cv.frame(pad, pad, cv.w - pad, cv.h - pad, mid, t=t, alpha=190)
    m = max(14, min(cv.w, cv.h) // 12)
    cv.rect(pad, pad, pad + m, pad + t * 3, ink, alpha=130)
    cv.rect(pad, pad, pad + t * 3, pad + m, ink, alpha=130)
    cv.rect(cv.w - pad - m, pad, cv.w - pad, pad + t * 3, ink, alpha=130)
    cv.rect(cv.w - pad - t * 3, pad, cv.w - pad, pad + m, ink, alpha=130)
    cv.rect(pad, cv.h - pad - t * 3, pad + m, cv.h - pad, ink, alpha=130)
    cv.rect(pad, cv.h - pad - m, pad + t * 3, cv.h - pad, ink, alpha=130)
    cv.rect(cv.w - pad - m, cv.h - pad - t * 3, cv.w - pad, cv.h - pad, ink, alpha=130)
    cv.rect(cv.w - pad - t * 3, cv.h - pad - m, cv.w - pad, cv.h - pad, ink, alpha=130)

    # ラベル
    s = max(1, min(cv.w, cv.h) // 150)
    cv.text_center("PLACEHOLDER", int(cv.h * 0.70), ink, scale=max(1, s - 1), alpha=140)
    cv.text_center(label.upper(), int(cv.h * 0.78), ink, scale=s)
    cv.text_center("%d x %d" % (cv.w, cv.h), int(cv.h * 0.86), ink,
                   scale=max(1, s - 1), alpha=190)


def draw_logo(cv, label, idx):
    """ロゴ（透過PNG）"""
    ink = (74, 38, 12)
    x = int(cv.h * 0.95)
    s = max(2, cv.h // 14)
    while s > 1 and x + text_size(label, s)[0] > cv.w:
        s -= 1                       # 文字が右端で切れないように縮める
    cv.disc(cv.h * 0.5, cv.h * 0.5, cv.h * 0.30, (226, 97, 11), alpha=255)
    cv.text(label.upper(), x, (cv.h - GLYPH_H * s) // 2, ink, scale=s)


def draw_deco(cv, label, idx):
    """背景装飾（透過PNG）"""
    base, mid, ink = TINTS[idx % len(TINTS)]
    r = min(cv.w, cv.h) * 0.46
    cv.disc(cv.w / 2, cv.h / 2, r, mid, alpha=95)
    cv.disc(cv.w * 0.30, cv.h * 0.30, r * 0.42, base, alpha=150)
    cv.text_center(label.upper(), cv.h // 2, ink, scale=max(1, cv.w // 220), alpha=120)


def draw_og(cv, label, idx):
    base, mid, ink = TINTS[0]
    cv.rect(0, 0, cv.w, cv.h, base)
    cv.hatch(mid, gap=40, t=4, alpha=45)
    cv.disc(cv.w * 0.5, cv.h * 0.36, cv.h * 0.22, mid, alpha=120)
    cv.text_center("PORTFOLIO SITE", int(cv.h * 0.66), ink, scale=5)
    cv.text_center("OG IMAGE %d x %d" % (cv.w, cv.h), int(cv.h * 0.80), ink,
                   scale=3, alpha=190)


def draw_favicon(cv, label, idx):
    cv.rect(0, 0, cv.w, cv.h, (226, 97, 11))
    cv.disc(cv.w * 0.5, cv.h * 0.5, cv.w * 0.34, (255, 255, 255), alpha=255)
    cv.text_center("PF", cv.h // 2, (226, 97, 11), scale=max(2, cv.w // 90))


STYLES = {
    "photo": draw_photo,
    "logo": draw_logo,
    "deco": draw_deco,
    "og": draw_og,
    "favicon": draw_favicon,
}

# ------------------------------------------------------- 画像マニフェスト
# (ファイル名, 幅, 高さ, ラベル, スタイル, 用途メモ)
IMAGES = [
    ("logo.png", 320, 96, "izumi", "logo", "ヘッダー / フッターのロゴ（透過PNG推奨）"),

    ("favicon.png", 512, 512, "if", "favicon", "ファビコン / Apple タッチアイコン"),

    ("og-image.png", 1200, 630, "og", "og", "OGP / X カード"),

    ("hero-main.png", 1400, 1050, "hero main", "photo", "TOP ヒーロー メイン画像 (4:3)"),
    ("hero-sub-01.png", 600, 600, "hero sub 01", "photo", "TOP ヒーロー サブ画像 (1:1)"),
    ("hero-sub-02.png", 600, 600, "hero sub 02", "photo", "TOP ヒーロー サブ画像 (1:1)"),
    ("hero-sub-03.png", 600, 600, "hero sub 03", "photo", "TOP ヒーロー サブ画像 (1:1)"),

    ("about-main.png", 1000, 1250, "about main", "photo", "ABOUT ポートレート (4:5)"),
    ("about-sub.png", 900, 900, "about sub", "photo", "ABOUT BACKGROUND 画像 (1:1)"),

    ("works-01.png", 1000, 1000, "works 01", "photo", "WORKS サムネイル (1:1)"),
    ("works-02.png", 1000, 1000, "works 02", "photo", "WORKS サムネイル (1:1)"),
    ("works-03.png", 1000, 1000, "works 03", "photo", "WORKS サムネイル (1:1)"),
    ("works-04.png", 1000, 1000, "works 04", "photo", "WORKS サムネイル (1:1)"),
    ("works-05.png", 1000, 1000, "works 05", "photo", "WORKS サムネイル (1:1)"),
    ("works-06.png", 1000, 1000, "works 06", "photo", "WORKS サムネイル (1:1)"),
    ("works-07.png", 1000, 1000, "works 07", "photo", "WORKS サムネイル (1:1)"),
    ("works-08.png", 1000, 1000, "works 08", "photo", "WORKS サムネイル (1:1)"),
    ("works-09.png", 1000, 1000, "works 09", "photo", "WORKS サムネイル (1:1)"),
    ("works-10.png", 1000, 1000, "works 10", "photo", "WORKS サムネイル (1:1)"),

    ("event-main.png", 1200, 900, "event main", "photo", "EVENT 導入ビジュアル (4:3)"),
    ("event-01.png", 1200, 900, "event 01", "photo", "EVENT 各プログラムの写真 (4:3)"),
    ("event-02.png", 1200, 900, "event 02", "photo", "EVENT 各プログラムの写真 (4:3)"),
    ("event-03.png", 1200, 900, "event 03", "photo", "EVENT 各プログラムの写真 (4:3)"),

    ("deco-01.png", 480, 480, "deco 01", "deco", "背景装飾（透過PNG）"),
    ("deco-02.png", 480, 480, "deco 02", "deco", "背景装飾（透過PNG）"),
    ("deco-03.png", 480, 480, "deco 03", "deco", "背景装飾（透過PNG）"),
]


def main():
    if "--list" in sys.argv:
        print("%-22s %-11s %s" % ("FILE", "SIZE", "USAGE"))
        print("-" * 78)
        for (name, w, h, _label, _style, memo) in IMAGES:
            print("%-22s %-11s %s" % (name, "%dx%d" % (w, h), memo))
        print("\n合計 %d ファイル" % len(IMAGES))
        return

    force = "--force" in sys.argv
    made = skipped = 0
    for i, (name, w, h, label, style, _memo) in enumerate(IMAGES):
        path = os.path.join(OUT_DIR, name)
        if os.path.exists(path) and not force:
            skipped += 1  # 差し替え済みの本番画像を上書きしないため
            continue
        transparent = style in ("logo", "deco")
        bg = (255, 255, 255, 0) if transparent else (255, 255, 255, 255)
        cv = Canvas(w, h, bg)
        STYLES[style](cv, label, i)
        cv.write(path)
        made += 1
    print("%d generated / %d skipped  ->  images/" % (made, skipped))
    if skipped and not force:
        print("既存ファイルはスキップしました（すべて作り直すには --force）")


if __name__ == "__main__":
    main()
