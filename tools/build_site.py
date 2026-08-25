# -*- coding: utf-8 -*-
"""
content.txt からサイトのHTMLを生成するスクリプト（標準ライブラリのみ）

    python tools/build_site.py

テキストの編集は content.txt だけで行い、このコマンドでHTMLへ反映します。
HTMLは毎回上書きされるため、HTMLを直接編集しないでください。
レイアウトそのものを変えたい場合は、このファイル内のテンプレートを編集します。
"""

import io
import math
import os
import random
import re
import unicodedata
from xml.sax.saxutils import escape as _esc

try:                     # 日本語やスペースを含むファイル名をURLに変換する
    from urllib.parse import quote
except ImportError:      # Python 2
    from urllib import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content.txt")
IMG_DIR = "images"


# ------------------------------------------------------------------ 解析
class Rec(object):
    """content.txt の [ ] ひとかたまり"""

    def __init__(self, kind, name):
        self.kind = kind
        self.name = name
        self.items = []          # 書かれた順の (項目名, 内容)

    def add(self, key, value):
        self.items.append([key, value])

    def extend_last(self, text):
        if self.items:
            self.items[-1][1] = (self.items[-1][1] + text).strip()

    def get(self, key, default=u""):
        for (k, v) in self.items:
            if k == key and v:
                return v
        return default

    def all(self, key):
        return [v for (k, v) in self.items if k == key and v]

    def pairs(self, key, sep=u"|", n=2):
        """「a | b」形式の行を分解して返す"""
        out = []
        for v in self.all(key):
            parts = [p.strip() for p in v.split(sep)]
            while len(parts) < n:
                parts.append(u"")
            out.append(parts[:n])
        return out


def parse(path):
    records = []
    cur = None
    with io.open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip(u"\r\n")
            s = line.strip()
            if not s or s.startswith(u"#"):
                continue
            if s.startswith(u"[") and s.endswith(u"]"):
                parts = s[1:-1].split(None, 1)
                cur = Rec(parts[0], parts[1] if len(parts) > 1 else u"")
                records.append(cur)
                continue
            if cur is None:
                raise SystemExit(u"content.txt %d行目: [ ] の見出しより前に内容があります" % lineno)
            if u":" in s:
                k, v = s.split(u":", 1)
                cur.add(k.strip(), v.strip())
            else:
                cur.extend_last(s)   # 前の項目の続き
    return records


def find(records, kind, name=None):
    for r in records:
        if r.kind == kind and (name is None or r.name == name):
            return r
    return Rec(kind, name or u"")


def find_all(records, kind):
    return [r for r in records if r.kind == kind]


def e(s):
    """HTMLとして安全な文字に変換"""
    return _esc(s or u"")


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def rich(s):
    """本文用。エスケープしたうえで [表示テキスト](リンク先) をリンクに変換する"""
    return LINK_RE.sub(lambda m: u'<a href="%s">%s</a>' % (m.group(2), m.group(1)), e(s))


def asset_ver(relpath):
    """ファイルの更新時刻。?v= に付けてブラウザの古いキャッシュを避ける"""
    path = os.path.join(ROOT, relpath)
    return u"%d" % int(os.path.getmtime(path)) if os.path.exists(path) else u"1"


def img(name):
    """image: の値を画像パスに（.png は省略可）

    画像を同じ名前で差し替えたときにブラウザが古い画像を出さないよう、
    ファイルの更新時刻を ?v= として付けます。
    """
    name = (name or u"").strip()
    if not name:
        return u""
    if not name.lower().endswith(u".png"):
        name += u".png"
    rel = u"%s/%s" % (IMG_DIR, name)
    return u"%s?v=%s" % (rel, asset_ver(rel))


# -------------------------------------------------------------- 部品HTML
IG_PATH = ("M12 2.2c3.2 0 3.6 0 4.9.1 1.2.1 1.8.3 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1 "
           ".4 2.2.1 1.3.1 1.7.1 4.9s0 3.6-.1 4.9c-.1 1.2-.3 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1 "
           ".4-2.2.4-1.3.1-1.7.1-4.9.1s-3.6 0-4.9-.1c-1.2-.1-1.8-.3-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1-.4-2.2-.1-1.3-.1-1.7-.1-4.9s0-3.6.1-4.9c.1-1.2.3-1.8.4-2.2.2-.6.5-1 "
           ".9-1.4.4-.4.8-.7 1.4-.9.4-.2 1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2zm0 3.2A6.6 6.6 0 1 0 18.6 12 6.6 6.6 0 0 0 12 "
           "5.4zm0 2.3a4.3 4.3 0 1 1 0 8.6 4.3 4.3 0 0 1 0-8.6zm5.4-2.6a1.5 1.5 0 1 1 0 3.1 1.5 1.5 0 0 1 0-3.1z")

def sns(indent, extra_class=u""):
    p = u" " * indent
    cls = u"sns" + (u" " + extra_class if extra_class else u"")
    return (
        p + u'<ul class="%s">\n' % cls
        + p + u'  <li><a href="%s" aria-label="Instagram"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="%s"/></svg></a></li>\n' % (e(SITE_IG), IG_PATH)
        + p + u'</ul>'
    )


def header_sub(indent):
    p = u" " * indent
    return (
        p + u'<div class="header__sub">\n'
        + sns(indent + 2) + u'\n'
        + p + u'</div>'
    )


def header(current):
    items = u"\n".join(
        u'        <li><a class="nav__link" href="%s"%s>%s</a></li>'
        % (e(href), u' aria-current="page"' if href == current else u"", e(label))
        for (href, label) in NAV
    )
    return u"""<!-- ============================================================ HEADER -->
<header class="header">
  <div class="wrap wrap--wide header__inner">
    <a class="header__logo" href="index.html">
      <img src="%(logo)s" alt="%(site)s" width="320" height="96">
    </a>

    <button class="burger" type="button" aria-label="メニューを開く" aria-expanded="false" aria-controls="global-nav">
      <span></span><span></span><span></span>
    </button>

    <nav class="nav" id="global-nav" aria-label="メインメニュー">
      <ul class="nav__list">
%(items)s
      </ul>

%(sub_in)s
    </nav>

%(sub_out)s
  </div>
</header>""" % {
        "logo": img("logo"),
        "site": e(SITE_NAME),
        "items": items,
        "sub_in": header_sub(6),
        "sub_out": header_sub(4),
    }


def footer(foot):
    menu = u"\n".join(u'          <li><a href="%s">%s</a></li>' % (e(h), e(l)) for (h, l) in NAV)
    sub = u"\n".join(u'          <li>%s</li>' % e(x) for x in foot.all("item"))
    return u"""<!-- ============================================================ FOOTER -->
<footer class="footer">
  <div class="wrap wrap--wide">
    <div class="footer__top">
      <div>
        <p class="footer__logo"><img src="%(logo)s" alt="%(site)s" width="320" height="96"></p>
        <p class="footer__lead">%(tagline)s</p>
%(sns)s
      </div>

      <nav aria-label="フッターメニュー">
        <p class="footer__head">Menu</p>
        <ul class="footer__list">
%(menu)s
        </ul>
      </nav>

      <nav aria-label="フッターサブメニュー">
        <p class="footer__head">%(fhead)s</p>
        <ul class="footer__list">
%(sub)s
        </ul>
      </nav>
    </div>

    <div class="footer__bottom">
      <p>&copy; <span data-year>2026</span> %(site)s</p>
      <p><a href="privacy.html">Privacy Policy</a></p>
    </div>
  </div>
</footer>

<a class="to-top" href="#main" aria-label="ページの先頭へ戻る"></a>

<script src="assets/js/main.js?v=%(jsver)s"></script>
</body>
</html>
""" % {
        "logo": img("logo"),
        "site": e(SITE_NAME),
        "tagline": e(SITE_TAGLINE),
        "sns": sns(8, "u-mt-m"),
        "menu": menu,
        "fhead": e(foot.get("head", u"Information")),
        "jsver": asset_ver("assets/js/main.js"),
        "sub": sub,
    }


MODAL = u"""<!-- ==================================== 詳細ポップアップ（共通） -->
<dialog class="modal" data-modal aria-labelledby="modal-title">
  <button class="modal__close" type="button" data-modal-close aria-label="閉じる"></button>
  <div class="modal__inner">
    <div class="modal__media">
      <img data-modal-image src="" alt="" width="1000" height="1000">
    </div>
    <div class="modal__body">
      <div class="tag-row" data-modal-tags></div>
      <h2 class="modal__title" id="modal-title" data-modal-title></h2>
      <div class="modal__detail" data-modal-detail></div>
    </div>
  </div>
</dialog>
"""

PAGE = u"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{favicon}" type="image/png">
<link rel="apple-touch-icon" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/style.css?v={cssver}">
<script>document.documentElement.classList.add("js");</script>
</head>
<body>
<a class="skip-link" href="#main">本文へスキップ</a>

{header}

<main id="main">
{body}
</main>

{modal}
{footer}"""


def page_head(en, catch, lead, crumb, deco):
    parts = [
        u'  <section class="page-head">',
        u'    <div class="wrap">',
        u'      <ul class="breadcrumb">',
        u'        <li><a href="index.html">Top</a></li>',
        u'        <li>%s</li>' % e(crumb),
        u'      </ul>',
        u'      <h1 class="page-head__title">%s</h1>' % e(en),
    ]
    if catch:
        parts.append(u'      <p class="page-head__catch">%s</p>' % e(catch))
    if lead:
        parts.append(u'      <p class="page-head__jp">%s</p>' % e(lead))
    parts += [u'    </div>', u'  </section>', u'']
    return u"\n".join(parts)


def sec_head(rec, keys=("label", "title", "catch", "lead"), center=False, indent=6):
    p = u" " * indent
    label, title, catch, lead = (rec.get(k) for k in keys)
    out = [p + u'<div class="sec-head%s reveal">' % (u" sec-head--center" if center else u"")]
    if label:
        out.append(p + u'  <span class="label-en">%s</span>' % e(label))
    if title:
        out.append(p + u'  <h2 class="sec-head__title">%s</h2>' % e(title))
    if catch:
        out.append(p + u'  <p class="sec-head__catch">%s</p>' % e(catch))
    if lead:
        out.append(p + u'  <p class="sec-lead">%s</p>' % rich(lead))
    out.append(p + u'</div>')
    return u"\n".join(out)


def contact_cta(contact, catch=None, lead=None):
    """各ページ下部のお問い合わせ導線"""
    out = [u'  <section class="section section--tint">',
           u'    <div class="wrap wrap--narrow">',
           u'      <div class="sec-head sec-head--center reveal">',
           u'        <span class="label-en">%s</span>' % e(contact.get("label", u"Contact")),
           u'        <h2 class="sec-head__title">%s</h2>' % e(contact.get("title", u"Contact"))]
    if catch:
        out.append(u'        <p class="sec-head__catch">%s</p>' % e(catch))
    if lead:
        out.append(u'        <p class="sec-lead">%s</p>' % e(lead))
    out += [u'      </div>',
            u'      <p class="hero__actions reveal u-center">',
            u'        <a class="btn" href="contact.html">お問い合わせフォーム</a>',
            u'      </p>',
            u'    </div>',
            u'  </section>']
    return u"\n".join(out)


# ------------------------------------------------------------ 作品カード
def cats_of(w):
    """category: の値をリストにする"""
    return [c.strip() for c in w.get("category").replace(u"、", u",").split(u",") if c.strip()]


def feature_tile(href, image, title, tags, size, indent=8, wide=False):
    """ホーム用の写真タイル。画像が主役で、押すと一覧ページの該当項目へ移動する"""
    p = u" " * indent
    out = [p + u'<a class="feature%s reveal" href="%s">' % (u" feature--wide" if wide else u"", e(href))]
    out.append(p + u'  <img src="%s" alt="%s" width="%d" height="%d" loading="lazy">'
               % (img(image), e(title), size[0], size[1]))
    out.append(p + u'  <span class="feature__arrow" aria-hidden="true"></span>')
    out.append(p + u'  <span class="feature__cap">')
    if tags:
        out.append(p + u'    <span class="feature__tags">%s</span>' % e(u" / ".join(tags)))
    out.append(p + u'    <span class="feature__title">%s</span>' % e(title))
    out.append(p + u'  </span>')
    out.append(p + u'</a>')
    return u"\n".join(out)


def slider(items_html, total, label, wide=False, indent=6):
    """横スライドするカード列。前後ボタンと「現在 / 総数」のカウンターを付ける"""
    p = u" " * indent
    return u"\n".join([
        p + u'<div class="slider%s" data-slider>' % (u" slider--wide" if wide else u""),
        p + u'  <div class="slider__track" data-slider-track tabindex="0" role="group" aria-label="%s">' % e(label),
        items_html,
        p + u'  </div>',
        p + u'  <div class="slider__nav">',
        p + u'    <button class="slider__btn slider__btn--prev" type="button" data-slider-prev aria-label="前のカードへ"></button>',
        p + u'    <p class="slider__count">',
        p + u'      <span data-slider-current>1</span>',
        p + u'      <span class="slider__total" data-slider-total>%d</span>' % total,
        p + u'    </p>',
        p + u'    <button class="slider__btn slider__btn--next" type="button" data-slider-next aria-label="次のカードへ"></button>',
        p + u'  </div>',
        p + u'</div>',
    ])


PROGRAM_DL = ((u"date", u"開催日"), (u"place", u"会場"), (u"target", u"対象"),
              (u"guests", u"参加人数"), (u"theme", u"テーマ"), (u"role", u"担当"))


def program_card(pr, indent=6):
    """EVENTページのプログラム1件。書かれている項目だけを表に出します"""
    p = u" " * indent
    out = [p + u'<article class="event reveal" id="%s">' % e(pr.get("image").replace(u".png", u"")),
           p + u'  <div class="event__thumb">',
           p + u'    <img src="%s" alt="%s" width="1200" height="900" loading="lazy">'
           % (img(pr.get("image")), e(pr.get("title"))),
           p + u'  </div>',
           p + u'  <div class="event__body">']
    tags = pr.all("tag")
    if tags:
        out.append(p + u'    <div class="tag-row">%s</div>'
                   % u"".join(u'<span class="tag tag--sm">%s</span>' % e(t) for t in tags))
    out.append(p + u'    <h2 class="event__title">%s</h2>' % e(pr.get("title")))
    if pr.get("catch"):
        out.append(p + u'    <p class="work__catch">%s</p>' % e(pr.get("catch")))
    for t in pr.all("text"):
        out.append(p + u'    <p class="work__desc">%s</p>' % rich(t))
    rows = [(label, pr.get(k)) for (k, label) in PROGRAM_DL if pr.get(k)]
    if rows:
        out.append(p + u'    <dl class="event__dl">')
        for (label, v) in rows:
            out.append(p + u'      <dt>%s</dt>' % e(label))
            out.append(p + u'      <dd>%s</dd>' % e(v))
        out.append(p + u'    </dl>')
    out += [p + u'  </div>', p + u'</article>']
    return u"\n".join(out)


def work_card(w, cat_label, indent=8):
    """カードは画像・題名・タグのみ。詳細は .card__detail に入れ、ポップアップで表示する"""
    p = u" " * indent
    cats = cats_of(w)
    title = w.get("title")
    out = [p + u'<article class="card reveal" id="%s" data-filter-target="works" data-category="%s">'
           % (e(w.get("image")), e(u" ".join(cats)))]
    out.append(p + u'  <button class="card__thumb card__open" type="button" aria-haspopup="dialog" aria-label="%s の詳細を見る">'
               % e(title))
    out.append(p + u'    <img src="%s" alt="%s" width="1000" height="1000" loading="lazy">'
               % (img(w.get("image")), e(title)))
    out.append(p + u'    <span class="card__zoom" aria-hidden="true"></span>')
    out.append(p + u'  </button>')
    out.append(p + u'  <div class="card__body">')
    if cats:
        out.append(p + u'    <div class="tag-row">%s</div>'
                   % u"".join(u'<span class="tag tag--sm">%s</span>' % e(cat_label.get(c, c)) for c in cats))
    out.append(p + u'    <h3 class="card__title">%s</h3>' % e(title))
    out.append(p + u'  </div>')

    # ポップアップに複製される詳細（HTMLには残るので検索エンジンからも読めます）
    out.append(p + u'  <div class="card__detail">')
    if w.get("catch"):
        out.append(p + u'    <p class="work__catch">%s</p>' % e(w.get("catch")))
    for t in w.all("text"):
        out.append(p + u'    <p class="work__desc">%s</p>' % rich(t))
    if w.get("role"):
        out.append(p + u'    <p class="work__role">%s</p>' % e(w.get("role")))
    out.append(p + u'  </div>')
    out.append(p + u'</article>')
    return u"\n".join(out)


# =============================================================== 読み込み
if not os.path.exists(SRC):
    raise SystemExit(u"content.txt が見つかりません: %s" % SRC)

recs = parse(SRC)

site = find(recs, "site")
SITE_NAME = site.get("name", u"PORTFOLIO")
SITE_TAGLINE = site.get("tagline")
SITE_IG = site.get("instagram", u"#")
SITE_EMAIL = site.get("email", u"")
SITE_FORM_ACTION = site.get("form_action", u"")
BASE_URL = site.get("base_url", u"")

NAV = find(recs, "nav").pairs("item")
FOOT = find(recs, "footer")

hero = find(recs, "hero")
works = find(recs, "works")
WORKS = find_all(recs, "work")
event = find(recs, "event")
PROGRAMS = find_all(recs, "program")
about = find(recs, "about")
fields_sec = find(recs, "fields")
FIELDS = find_all(recs, "field")
contact = find(recs, "contact")
privacy = find(recs, "privacy")

filters = find(recs, "filter").pairs("item", n=3)
CAT_LABEL = dict((k, l) for (k, l, _n) in filters)

# 画像の存在チェック（差し替え漏れ・打ち間違いの早期発見）
missing = []
for r in recs:
    for (k, v) in r.items:
        if k.startswith("image") or k == "intro_image":
            if v and not os.path.exists(os.path.join(ROOT, img(v).split(u"?")[0])):
                missing.append(u"[%s %s] %s: %s" % (r.kind, r.name, k, v))
if missing:
    print(u"警告: images/ に見つからない画像があります")
    for m in missing:
        print(u"  " + m)
    print(u"")


# ================================================================== INDEX
btn = (hero.pairs("button") or [[u"View Works", u"works.html"]])[0]
btn_ghost = (hero.pairs("button_ghost") or [[u"Contact", u"contact.html"]])[0]

hero_text = u"\n".join(u'          <p class="hero__lead">%s</p>' % rich(t)
                       for t in hero.all("text"))
hero_subs = u"\n".join(
    u'            <figure><img src="%s" alt="制作物のサンプル %d" width="600" height="600"></figure>'
    % (img(v), i + 1) for (i, v) in enumerate(hero.all("image_sub")))
scroll_cue = (u'          <p class="scroll-cue" aria-hidden="true">'
              u'<span class="scroll-cue__text">%s</span>'
              u'<span class="scroll-cue__line"></span></p>' % e(hero.get("scroll_label"))
              ) if hero.get("scroll_label") else u""

# TOPに並べる作品（content.txt の pickup: の順）
pickup = [x.strip() for x in works.get("pickup").replace(u"、", u",").split(u",") if x.strip()]
pickup_keys = [p.replace(u".png", u"") for p in pickup]
pickup_items = [w for w in WORKS if w.get("image").replace(u".png", u"") in pickup_keys]
pickup_html = slider(
    u"\n".join(
        feature_tile(u"works.html#%s" % w.get("image").replace(u".png", u""),
                     w.get("image"), w.get("title"),
                     [CAT_LABEL.get(c, c) for c in cats_of(w)], (1000, 1000), indent=10)
        for w in pickup_items
    ),
    len(pickup_items), u"WORKS のスライド",
)

program_cards = slider(
    u"\n".join(
        feature_tile(u"event.html#%s" % pr.get("image").replace(u".png", u""),
                     pr.get("image"), pr.get("title"), pr.all("tag"),
                     (1200, 900), indent=10, wide=True)
        for pr in PROGRAMS
    ),
    len(PROGRAMS), u"EVENT のスライド", wide=True,
)

index_body = u"""  <!-- ========================================================== HERO -->
  <section class="hero">
    <div class="wrap wrap--wide">
      <div class="hero__grid">
        <div class="hero__copy reveal">
          <span class="label-en label-en--long">%(hero_label)s</span>
          <h1 class="hero__catch hero__catch--jp" data-anim="chars">%(hero_catch)s<em>%(hero_em)s</em></h1>
%(hero_text)s
          <div class="hero__actions">
            <a class="btn" href="%(btn_href)s">%(btn_label)s</a>
            <a class="btn btn--ghost" href="%(gbtn_href)s">%(gbtn_label)s</a>
          </div>
%(scroll)s
        </div>

        <div class="hero__visual reveal">
          <div class="hero__main">
            <img src="%(hero_img)s" alt="代表作のビジュアル" width="1400" height="1050">
          </div>
          <div class="hero__subs">
%(hero_subs)s
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ========================================================= WORKS -->
  <section class="section">
    <div class="wrap wrap--wide">
%(works_head)s

%(pickup)s

      <p class="hero__actions reveal u-center u-mt-l">
        <a class="btn btn--ghost" href="works.html">すべての Works を見る</a>
      </p>
    </div>
  </section>

  <!-- ========================================================= EVENT -->
  <section class="section section--pale">
    <div class="wrap wrap--wide">
%(event_head)s

%(programs)s

      <p class="hero__actions reveal u-center u-mt-l">
        <a class="btn btn--ghost" href="event.html">Event の詳細を見る</a>
      </p>
    </div>
  </section>

  <!-- ========================================================= ABOUT -->
  <section class="section">
    <div class="wrap">
      <div class="profile">
        <div class="profile__photo reveal">
          <img src="%(about_img)s" alt="%(about_jp)s のポートレート" width="1000" height="1250" loading="lazy">
        </div>
        <div class="profile__body reveal">
          <span class="label-en">%(about_label)s</span>
          <h2 class="profile__name">%(about_n1)s<br>%(about_n2)s<small>%(about_small)s</small></h2>
          <div class="profile__text u-mt-m">
%(about_text)s
          </div>
          <p class="pull-quote">%(about_quote)s</p>
          <p class="hero__actions">
            <a class="btn btn--ghost" href="about.html">About をもっと見る</a>
          </p>
        </div>
      </div>
    </div>
  </section>

%(cta)s
""" % {
    "hero_label": e(hero.get("label")),
    "hero_catch": e(hero.get("catch")),
    "hero_em": e(hero.get("catch_em")),
    "hero_text": hero_text,
    "btn_label": e(btn[0]),
    "btn_href": e(btn[1]),
    "gbtn_label": e(btn_ghost[0]),
    "gbtn_href": e(btn_ghost[1]),
    "scroll": scroll_cue,
    "hero_img": img(hero.get("image")),
    "hero_subs": hero_subs,
    "works_head": sec_head(works),
    "pickup": pickup_html,
    "event_head": sec_head(event),
    "programs": program_cards,
    "about_img": img(about.get("image")),
    "about_jp": e(about.get("name_jp")),
    "about_label": e(about.get("label", u"About")),
    "about_n1": e(about.get("name_line1")),
    "about_n2": e(about.get("name_line2")),
    "about_small": e(u"%s / %s" % (about.get("name_jp"), about.get("role_label"))),
    "about_text": u"\n".join(u'            <p>%s</p>' % rich(t) for t in about.all("top_text")),
    "about_quote": e(about.get("quote")),
    "cta": contact_cta(contact, contact.get("catch"), contact.get("lead")),
}

# ================================================================== WORKS
filter_btns = u"\n".join(
    u'        <button class="filter__btn%s" type="button" data-category="%s" aria-pressed="%s" title="%s">%s</button>'
    % (u" is-active" if k == "all" else u"", e(k), u"true" if k == "all" else u"false", e(note), e(label))
    for (k, label, note) in filters
)

works_body = page_head(works.get("title", u"Works"), works.get("catch"),
                       works.get("lead"), works.get("title", u"Works"), "deco-01") + u"""
  <section class="section">
    <div class="wrap wrap--wide">
      <p class="sec-lead reveal">%(page_lead)s</p>

      <div class="filter u-mt-l" data-filter-group="works" role="group" aria-label="カテゴリーで絞り込む">
%(filters)s
      </div>
      <p class="result-count"><span data-filter-count="works">%(count)d</span> works</p>

      <div class="grid grid--4">
%(cards)s
      </div>
    </div>
  </section>

%(cta)s
""" % {
    "page_lead": rich(works.get("page_lead")),
    "filters": filter_btns,
    "count": len(WORKS),
    "cards": u"\n".join(work_card(w, CAT_LABEL) for w in WORKS),
    "cta": contact_cta(contact, contact.get("cta_works_catch"), contact.get("cta_works_lead")),
}

# ================================================================== EVENT
event_body = page_head(event.get("title", u"Event"), event.get("catch"),
                       event.get("lead"), event.get("title", u"Event"), "deco-02") + u"""
  <section class="section">
    <div class="wrap">
      <div class="grid">
%(programs)s
      </div>
    </div>
  </section>

%(cta)s
""" % {
    "programs": u"\n".join(program_card(pr) for pr in PROGRAMS),
    "cta": contact_cta(contact, contact.get("cta_event_catch")),
}

# ================================================================== ABOUT
fields_html = u"\n".join(
    u"""        <div class="svc reveal">
          <span class="tag">%s</span>
          <p class="work__desc">%s</p>
        </div>""" % (e(f.get("name")), rich(f.get("text"))) for f in FIELDS
)

about_body = page_head(u"About", about.get("name_jp"), about.get("lead_jp"), u"About", "deco-03") + u"""
  <section class="section">
    <div class="wrap">
      <div class="profile">
        <div class="profile__photo reveal">
          <img src="%(img)s" alt="%(name_jp)s のポートレート" width="1000" height="1250">
        </div>
        <div class="profile__body reveal">
          <span class="label-en">%(role)s</span>
          <h2 class="profile__name">%(n1)s<br>%(n2)s<small>%(name_jp)s</small></h2>
          <div class="profile__text u-mt-m">
%(text)s
          </div>
          <p class="pull-quote">%(quote)s</p>
          <div class="profile__text">
%(text_after)s
          </div>
          <p class="work__role">%(based)s</p>
        </div>
      </div>
    </div>
  </section>


  <section class="section">
    <div class="wrap">
      <div class="sec-head reveal">
        <span class="label-en">%(f_label)s</span>
        <h2 class="sec-head__title">%(f_title)s</h2>
        <p class="sec-head__jp">%(f_jp)s</p>
      </div>
      <div class="grid grid--3">
%(fields)s
      </div>
    </div>
  </section>

%(cta)s
""" % {
    "img": img(about.get("image")),
    "name_jp": e(about.get("name_jp")),
    "role": e(about.get("role_label")),
    "n1": e(about.get("name_line1")),
    "n2": e(about.get("name_line2")),
    "text": u"\n".join(u'            <p>%s</p>' % rich(t) for t in about.all("text")),
    "quote": e(about.get("quote")),
    "text_after": u"\n".join(u'            <p>%s</p>' % rich(t) for t in about.all("text_after")),
    "based": e(about.get("based")),
    "f_label": e(fields_sec.get("label", u"Fields")),
    "f_title": e(fields_sec.get("title", u"Fields")),
    "f_jp": e(fields_sec.get("jp")),
    "fields": fields_html,
    "cta": contact_cta(contact, contact.get("cta_about_catch")),
}

# ================================================================ CONTACT
options = u"\n".join(u'            <option>%s</option>' % e(o) for o in contact.all("option"))

# 送信方法: [site] form_action: があればそこへ POST、なければメールソフトを開く（mailto）
if SITE_FORM_ACTION:
    FORM_ATTR = u'action="%s" method="post"' % e(SITE_FORM_ACTION)
    FORM_MSG = u"送信しました。ありがとうございます。"
elif SITE_EMAIL:
    FORM_ATTR = (u'action="mailto:%s" method="post" enctype="text/plain"'
                 u' data-mail-form data-mail-to="%s" data-mail-subject="%s"'
                 % (e(SITE_EMAIL), e(SITE_EMAIL), e(u"【お問い合わせ】" + SITE_NAME)))
    FORM_MSG = u"メールソフトが開きます。内容を確認して、そのまま送信してください。"
else:
    FORM_ATTR = u'action="#" method="post" data-mail-form'
    FORM_MSG = u"送信先メールアドレスが未設定です（content.txt の [site] email: を記入してください）"

contact_body = page_head(contact.get("title", u"Contact"), contact.get("catch"),
                         contact.get("page_lead_jp"), contact.get("title", u"Contact"),
                         "deco-01") + u"""
  <section class="section">
    <div class="wrap wrap--narrow">
      <div class="profile__text reveal">
        <p>%(intro)s</p>
      </div>

      <form class="form u-mt-l reveal" %(form_attr)s>
        <p class="tag" data-form-message hidden tabindex="-1">%(form_msg)s</p>

        <div class="form__row">
          <label class="form__label" for="f-name">お名前<span class="req">必須</span></label>
          <input id="f-name" name="name" type="text" required autocomplete="name" placeholder="山田 花子">
        </div>

        <div class="form__row">
          <label class="form__label" for="f-company">会社名・団体名</label>
          <input id="f-company" name="company" type="text" autocomplete="organization" placeholder="株式会社○○">
        </div>

        <div class="form__row">
          <label class="form__label" for="f-email">メールアドレス<span class="req">必須</span></label>
          <input id="f-email" name="email" type="email" required autocomplete="email" placeholder="mail@example.com">
        </div>

        <div class="form__row">
          <label class="form__label" for="f-type">お問い合わせ種別<span class="req">必須</span></label>
          <select id="f-type" name="type" required>
            <option value="">選択してください</option>
%(options)s
          </select>
        </div>

        <div class="form__row">
          <label class="form__label" for="f-message">お問い合わせ内容<span class="req">必須</span></label>
          <textarea id="f-message" name="message" required placeholder="用途・スケジュール・ご予算など、決まっている範囲でご記入ください"></textarea>
        </div>

        <p class="form__note">
          ご記入いただいた個人情報は、お問い合わせへの回答のみに利用します。
          詳しくは<a href="privacy.html">プライバシーポリシー</a>をご覧ください。
        </p>

        <button class="btn form__submit" type="submit">送信する</button>
      </form>
    </div>
  </section>

""" % {
    "intro": rich(contact.get("form_intro", contact.get("lead"))),
    "options": options,
    "form_attr": FORM_ATTR,
    "form_msg": FORM_MSG,
}

# ================================================================ PRIVACY
prose = []
buf_li = []


def flush_li():
    if buf_li:
        prose.append(u'      <ul>')
        prose.extend(u'        <li>%s</li>' % rich(x) for x in buf_li)
        prose.append(u'      </ul>')
        del buf_li[:]


for (k, v) in privacy.items:
    if not v:
        continue
    if k == "h2":
        flush_li()
        prose.append(u'      <h2>%s</h2>' % e(v))
    elif k == "p":
        flush_li()
        prose.append(u'      <p>%s</p>' % rich(v))
    elif k == "li":
        buf_li.append(v)
flush_li()

privacy_body = page_head(u"Privacy Policy", privacy.get("catch"),
                         u"", u"Privacy Policy", "deco-03") + u"""
  <section class="section">
    <div class="wrap wrap--narrow prose">
%(body)s
      <p class="result-count u-mt-l">%(updated)s</p>
    </div>
  </section>
""" % {"body": u"\n".join(prose), "updated": e(privacy.get("updated"))}


# --------------------------------------------------- 文字アニメーション
# 見出しを <span> で包み、CSSでマスクからスライドアップさせる
UP_TARGETS = (
    "page-head__title", "page-head__catch",
    "sec-head__title", "sec-head__catch",
    "event__title", "profile__name",
)
UP_RE = re.compile(
    r'<(h1|h2|h3|p) class="([^"]*(?:%s)[^"]*)">(.*?)</\1>' % u"|".join(UP_TARGETS),
    re.S,
)


# ------------------------------------------------------ 背景装飾の散りばめ
# images/deco/ の画像を、ページ全体に散りばめます。
#   ・大きさはすべて同じ（下の DECO_SIZE）
#   ・重なり順はいちばん下（本文・写真の後ろに回ります）
#   ・セクションの境目に置くので、余白のすき間から見えます
DECO_DIR = os.path.join(IMG_DIR, "deco")
DECO_SM_DIR = os.path.join(IMG_DIR, "deco-sm")

DECO_PER_PAGE = 5                                # 1ページに置く枚数の目安
DECO_SIZE = u"clamp(128px, 21vw, 280px)"         # 大きさ（全部そろえる）
HERO_PIN = u"かにだんご"                          # TOPのキャッチコピー横に置く絵


def png_size(rel, default=(360, 360)):
    """PNGの幅・高さを読む（width/height 属性用）"""
    try:
        with open(os.path.join(ROOT, rel), "rb") as f:
            head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            import struct
            return struct.unpack(">II", head[16:24])
    except Exception:
        pass
    return default


def deco_files():
    """装飾画像の一覧

    images/deco/（元画像）を基準にし、images/deco-sm/ に表示用の縮小版があれば
    そちらを読み込みます。元画像を置かず deco-sm/ だけでも動きます。
    """
    src = os.path.join(ROOT, DECO_DIR)
    names = []
    if os.path.isdir(src):
        names = sorted(os.listdir(src))
    elif os.path.isdir(os.path.join(ROOT, DECO_SM_DIR)):
        names = sorted(os.listdir(os.path.join(ROOT, DECO_SM_DIR)))
    out = []
    for n in names:
        if not n.lower().endswith((u".png", u".jpg", u".jpeg", u".webp")):
            continue
        small = u"%s/%s" % (DECO_SM_DIR, n)
        if os.path.exists(os.path.join(ROOT, small)):
            out.append(small)
        elif os.path.exists(os.path.join(ROOT, DECO_DIR, n)):
            out.append(u"%s/%s" % (DECO_DIR, n))
    return out


DECOS = deco_files()


class DecoDeck(object):
    """同じ絵が近くに出ないよう、全種類を1巡してから次の順番を配り直す"""

    RECENT = 3        # 直前に使った数枚は、次の巡でも後ろへ回す

    def __init__(self, rnd, items):
        self.rnd = rnd
        self.items = list(items)
        self.deck = []
        self.recent = []

    def draw(self):
        if not self.items:
            return None
        if not self.deck:
            deck = list(self.items)
            self.rnd.shuffle(deck)
            # 巡の境目でも同じ絵が近くに並ばないよう、直前に使った分を後ろへ
            head = [x for x in deck if x not in self.recent]
            tail = [x for x in deck if x in self.recent]
            self.deck = head + tail if head else deck
        item = self.deck.pop(0)
        self.recent = (self.recent + [item])[-self.RECENT:]
        return item


# 横位置は「左・中央・右」の3か所。同じ位置が近くで続かないよう順番に使います
DECO_X = {u"left": u"22%", u"center": u"50%", u"right": u"78%"}

# セクションごとの余白の高さ（CSSの padding-block と同じ値）
BAND_TOP = {
    u"hero": u"clamp(40px, 7vw, 96px)",
    u"section": u"var(--sec-y)",
    u"page-head": u"clamp(44px, 7vw, 88px)",
}
BAND_BOTTOM = {
    u"hero": u"clamp(60px, 9vw, 120px)",
    u"section": u"var(--sec-y)",
    u"page-head": u"clamp(28px, 4vw, 44px)",
}
FOOTER_TOP = u"clamp(40px, 5vw, 60px)"


def deco_tag(rnd, rel, x, y, index):
    """装飾画像1枚ぶんのHTML"""
    # ファイル名は NFC に正規化してからURLにする
    # （macOSは濁点を分けて保存するが、GitHub上のファイル名は結合済みのため）
    src = u"%s?v=%s" % (quote(unicodedata.normalize("NFC", rel)), asset_ver(rel))
    rot = rnd.uniform(-20, 20)          # 回転しても余白に収まる範囲
    rad = math.radians(rot)
    k = abs(math.cos(rad)) + abs(math.sin(rad))   # 回転で広がる分
    style = u"--dx:%s;--dy:%s;--dr:%.1fdeg;--dk:%.3f" % (x, y, rot, k)
    iw, ih = png_size(rel)
    return (u'    <img class="deco deco--scatter deco--i%d" src="%s" alt=""'
            u' width="%d" height="%d" loading="lazy" decoding="async"'
            u' style="%s">' % (index, src, iw, ih, style))


SECTION_RE = re.compile(r'(?m)^(\s*)<section class="(hero|section|page-head)[^"]*">$')


def deco_slots(kinds):
    """装飾を置ける場所（セクションどうしの境目と、最後のセクションとフッターの境目）

    どちらも上下が余白どうしなので、文章・写真には重なりません。
    余白の高さが上下で違うときは、中心を広いほうへずらして中に収めます。
    戻り値は (差し込むセクション番号, --dy の値)
    """
    slots = []
    for i in range(len(kinds) - 1):
        above, below = BAND_BOTTOM[kinds[i]], BAND_TOP[kinds[i + 1]]
        slots.append((i + 1, u"calc((%s - %s) / 2)" % (below, above)))
    last = len(kinds) - 1
    slots.append((last, u"calc(100%% + (%s - %s) / 2)" % (FOOTER_TOP, BAND_BOTTOM[kinds[last]])))
    return slots


def deco_positions(rnd, n):
    """左・中央・右を、近くで同じ位置が続かないように並べる"""
    order = list(DECO_X.keys())
    rnd.shuffle(order)
    return [DECO_X[order[i % len(order)]] for i in range(n)]


def add_decor(html, seed, count=DECO_PER_PAGE):
    """ページに装飾画像を散りばめる（実際に見せる枚数は画面幅に応じてCSSが1〜5枚に調整）"""
    if not DECOS:
        return html
    matches = list(SECTION_RE.finditer(html))
    if not matches:
        return html

    rnd = random.Random(seed)
    slots = deco_slots([m.group(2) for m in matches])
    if len(slots) > count:                      # 多いときはページ全体に散らす
        step = (len(slots) - 1) / float(count - 1) if count > 1 else 0
        picked, used = [], set()
        for i in range(count):
            j = min(len(slots) - 1, max(0, int(round(i * step))))
            while j in used:
                j = (j + 1) % len(slots)
            used.add(j)
            picked.append(j)
        picked.sort()
        slots = [slots[j] for j in picked]

    # TOPの1枚目（ヒーロー直下）は決まった絵にする
    pool = list(DECOS)
    first = None
    if matches[0].group(2) == u"hero":
        pinned = [r for r in pool
                  if unicodedata.normalize("NFC", HERO_PIN)
                  in unicodedata.normalize("NFC", r)]
        if pinned:
            first = pinned[0]
            pool.remove(first)
    deck = DecoDeck(rnd, pool)

    xs = deco_positions(rnd, len(slots))
    per_section = {}
    for n, (sec_i, y) in enumerate(slots):
        rel = first if (n == 0 and first) else deck.draw()
        per_section.setdefault(sec_i, []).append(deco_tag(rnd, rel, xs[n], y, n + 1))

    out, pos = [], 0
    for i, m in enumerate(matches):
        out.append(html[pos:m.end()])
        pos = m.end()
        if i in per_section:
            out.append(u"\n" + u"\n".join(per_section[i]))
    out.append(html[pos:])
    return u"".join(out)


def add_text_anim(html):
    def repl(m):
        tag, cls, inner = m.group(1), m.group(2), m.group(3)
        if u"a-up" in cls:
            return m.group(0)
        cls += u" a-up a-up--d1" if u"catch" in cls else u" a-up"
        return u'<%s class="%s"><span>%s</span></%s>' % (tag, cls, inner, tag)

    return UP_RE.sub(repl, html)


# ================================================================== 書き出し
PAGES = [
    ("index.html", "index", "website", None, index_body),
    ("works.html", "works", "article", "works.html", works_body),
    ("event.html", "event", "article", "event.html", event_body),
    ("about.html", "about", "profile", "about.html", about_body),
    ("contact.html", "contact", "article", "contact.html", contact_body),
    ("privacy.html", "privacy", "article", None, privacy_body),
]

FOOTER_HTML = footer(FOOT)

for (fname, key, ogtype, current, body) in PAGES:
    meta = find(recs, "page", key)
    html = PAGE.format(
        title=e(meta.get("title", SITE_NAME)),
        desc=e(meta.get("description")),
        canonical=e(BASE_URL + (u"" if fname == "index.html" else fname)),
        ogtype=ogtype,
        og=img("og-image"),
        favicon=img("favicon"),
        cssver=asset_ver("assets/css/style.css"),
        header=header(current),
        body=add_decor(add_text_anim(body.rstrip()), key) + u"\n",
        modal=MODAL if u"card__open" in body else u"",
        footer=FOOTER_HTML,
    )
    with io.open(os.path.join(ROOT, fname), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(u"生成  %-14s %6d bytes" % (fname, len(html)))

print(u"\ncontent.txt から %d ページを生成しました（作品 %d件 / プログラム %d件）"
      % (len(PAGES), len(WORKS), len(PROGRAMS)))
