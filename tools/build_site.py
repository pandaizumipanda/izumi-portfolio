# -*- coding: utf-8 -*-
"""
content.txt からサイトのHTMLを生成するスクリプト（標準ライブラリのみ）

    python tools/build_site.py

表示文章の編集は 編集用/サイトの文章.txt で行い、このコマンドでHTMLへ反映します。
content.txt は構造・画像・元データ用です。
HTMLは毎回上書きされるため、HTMLを直接編集しないでください。
レイアウトそのものを変えたい場合は、このファイル内のテンプレートを編集します。
"""

import io
import os
import re
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


# ------------------------------------------------------------------ 新サイト
from pathlib import Path
from datetime import date
import hashlib
import json
from site_copy import Catalog
from urllib.parse import urljoin

records = parse(SRC)
site = find(records, 'site')
about = find(records, 'about')
speaking = find(records, 'speaking')
works = find_all(records, 'work')
programs = find_all(records, 'program')
base = site.get('base_url')

def asset(path):
    p = Path(ROOT) / path
    token = hashlib.sha256(p.read_bytes()).hexdigest()[:10] if p.exists() else '1'
    return quote(path) + '?v=' + token

def image_path(name):
    web = 'images/web/' + name + '.jpg'
    if (Path(ROOT) / web).exists():
        return web
    return 'images/' + (name if Path(name).suffix else name + '.png')

def image(name, alt, cls='', eager=False):
    return f'<img src="{asset(image_path(name))}" alt="{e(alt)}" class="{cls}" loading="{"eager" if eager else "lazy"}" decoding="async">'

def paras(values):
    return ''.join('<p>' + rich(v) + '</p>' for v in values)

def arrow():
    return '<span aria-hidden="true">↗</span>'

def link(url, label, cls='text-link'):
    return f'<a class="{cls}" href="{e(url)}">{e(label)}{arrow()}</a>'

def section_head(number, label, title, extra=''):
    return f'<div class="section-heading"><p class="eyebrow">({number}) {e(label)}</p><div><h2>{title}</h2>{extra}</div></div>'

def nav(active):
    links = [('event','Speaking'),('works','Works'),('about','About'),('contact','Contact')]
    items = ''.join(f'<a href="{key}.html" {"aria-current=page" if active == key else ""} class="{"nav-contact" if key == "contact" else ""}">{label}{arrow() if key == "contact" else ""}</a>' for key,label in links)
    return f'''<a class="skip" href="#main">本文へスキップ</a>
<header class="header"><a class="wordmark" href="index.html" aria-label="IZUMI FUKUYAMA ホーム">IZUMI<br>FUKUYAMA</a><span class="header-role">CREATOR &<br>VIBE CODING INSTRUCTOR</span><button class="menu-toggle" aria-controls="navigation" aria-expanded="false" type="button">Menu <span aria-hidden="true">＋</span></button><nav id="navigation" aria-label="メインナビゲーション">{items}</nav></header>'''

def cta():
    return f'''<section class="contact-band"><div class="contact-band-top"><p class="eyebrow">LET’S WORK TOGETHER</p><p>講演・ワークショップ、制作のご相談</p></div><a href="contact.html" class="contact-large">Let’s talk.<span aria-hidden="true">↗</span></a><div class="contact-band-bottom"><p>まだ、アイデアの段階でも。<br>まずは、お話を聞かせてください。</p><span>SPEAKING / DESIGN / CREATIVE</span></div></section>'''

def footer():
    ig=site.get('instagram')
    social=f'<a href="{e(ig)}" target="_blank" rel="noopener noreferrer">Instagram ↗</a>' if ig.startswith('https://') else ''
    return f'<footer class="footer"><a href="index.html">IZUMI FUKUYAMA</a><span>© {date.today().year} IZUMI FUKUYAMA</span><div>{social}<a href="privacy.html">Privacy policy</a><a href="#top">Back to top ↑</a></div></footer>'

def poster():
    return '''<div class="lecture-poster" aria-label="アイデアを言葉にし、AIと対話し、形にする制作プロセス"><div class="poster-top"><span>THE PROCESS OF CREATING</span><span>IF / 01</span></div><div class="orbital" aria-hidden="true"><i></i><i></i><i></i><span>✳</span></div><div class="poster-words">An idea.<br>A dialogue.<br>A possibility.</div><div class="poster-bottom"><span>考える。対話する。つくる。</span><span>VIBE CODING</span></div></div>'''

def lecture_visual(secondary=False):
    key = 'photo_secondary' if secondary else 'photo'
    photo=speaking.get(key)
    if photo and (Path(ROOT) / image_path(photo)).exists():
        return '<figure class="lecture-photo">' + image(photo,speaking.get(key + '_alt')) + '<figcaption>Speaking & Workshop / IZUMI FUKUYAMA</figcaption></figure>'
    return poster()

def card(w, index, detail=False):
    ident=w.get('image')
    if w.get('image_pending') == 'true':
        visual=f'<div class="project-type"><span>WEB APPLICATION</span><strong>{e(w.get("title"))}</strong><span>CONCEPT & DESIGN　↗</span></div>'
    else:
        visual=image(ident,w.get('title'))
    categories=w.get('category')
    return f'''<article class="project" data-category="{e(categories)}"><a class="project-image" href="works.html#{e(ident)}" {'data-project="'+e(ident)+'"' if detail else ''}>{visual}<span class="project-open" aria-hidden="true">↗</span></a><div class="project-caption"><div><p>{e(categories.replace(', ', ' / ').upper())}</p><h3><a href="works.html#{e(ident)}" {'data-project="'+e(ident)+'"' if detail else ''}>{e(w.get('title'))}</a></h3></div><span class="project-index">{index:02}</span></div></article>'''

def detail_block(w):
    ident=w.get('image')
    visual='' if w.get('image_pending') == 'true' else image(ident,w.get('title'))
    role=f'<p class="detail-role">ROLE / {e(w.get("role"))}</p>' if w.get('role') else ''
    return f'''<section class="project-detail" id="{e(ident)}" aria-labelledby="title-{e(ident)}"><div class="detail-visual">{visual}</div><div class="detail-copy"><p class="eyebrow">{e(w.get('category').replace(', ', ' / ').upper())}</p><h2 id="title-{e(ident)}">{e(w.get('title'))}</h2><h3>{e(w.get('catch'))}</h3>{paras(w.all('text'))}{role}</div></section>'''

def topics():
    return '<div class="topics">' + ''.join(f'<article class="topic"><div><span>{t.get("number")}</span><p class="eyebrow">{e(t.get("format"))}</p></div><h3>{e(t.get("title"))}</h3><p>{e(t.get("text"))}</p><p class="topic-detail">{e(t.get("detail"))}</p></article>' for t in find_all(records,'talk')) + '</div>'

def home():
    selected=[works[i] for i in [0,4,1,2]]
    return f'''<section class="hero hero-photographic"><div class="hero-visual"><div class="hero-photograph">{image(speaking.get('photo'),speaking.get('photo_alt'),eager=True)}</div><div class="hero-front wrap"><div class="hero-topline"><p>INDEPENDENT CREATOR / OSAKA, JAPAN</p><p>CREATING & SHARING POSSIBILITIES</p></div><div class="hero-display" aria-label="Think. Make. Share."><span>Think.</span><span>Make.</span><span class="serif">Share.</span></div><div class="hero-bottom"><span>福山 いずみ / VIBE CODING INSTRUCTOR</span><a href="#hero-intro">SCROLL TO EXPLORE ↓</a></div></div></div><div class="hero-copy wrap" id="hero-intro"><div><p class="eyebrow"><span class="status-dot"></span> VIBE CODING / SPEAKING</p><h1>{'<br>'.join(map(e,speaking.all('headline')))}</h1></div><div><p class="hero-description">{e(speaking.get('intro'))}</p>{link('event.html','講演・ワークショップについて','round-link')}<a class="hero-instagram" href="{e(site.get('instagram'))}" target="_blank" rel="noopener noreferrer">Instagram / @panda_love_izumi ↗</a></div></div></section>
<section id="speaking" class="speaking-section dark"><div class="wrap">{section_head('01','SPEAKING & WORKSHOP','つくる人の視点で、<br>AIの可能性をひらく。')}<div class="speaking-grid has-lecture-photo">{lecture_visual()}<div class="speaking-copy"><h3>{'<br>'.join(map(e,speaking.all('statement')))}</h3>{paras(speaking.all('text'))}{link('event.html','講演・ワークショップを見る','button light')}<p class="small-note">{e(speaking.get('note'))}</p></div></div><div class="speaking-strip"><span>LECTURE</span><span>HANDS-ON WORKSHOP</span><span>CREATIVE TALK</span></div></div></section>
<section class="work-section wrap">{section_head('02','SELECTED WORKS','考えたことを、<br>かたちに。',link('works.html','すべての制作を見る'))}<div class="project-grid selected-grid">{''.join(card(w,works.index(w)+1) for w in selected)}</div></section>
<section class="about-section wrap">{section_head('03','ABOUT','つくることが、<br>伝えることにつながる。')}<div class="about-home"><figure>{image('about-main','福山いずみのプロフィール写真')}<figcaption>IZUMI FUKUYAMA / BASED IN OSAKA</figcaption></figure><div><p class="eyebrow">CREATOR / VIBE CODING INSTRUCTOR</p><h3>福山 いずみ<span>Izumi Fukuyama</span></h3>{paras(about.all('top_text'))}{link('about.html','プロフィールを見る')}<a class="profile-instagram" href="{e(site.get('instagram'))}" target="_blank" rel="noopener noreferrer">Instagram / @panda_love_izumi ↗</a></div></div></section>{cta()}'''

def page_intro(label, title, description):
    return f'<section class="page-intro wrap"><p class="eyebrow">IZUMI FUKUYAMA / {e(label.upper())}</p><h1>{title}</h1><p class="page-intro-description">{e(description)}</p></section>'

def speaking_page():
    approach=''.join(f'<article class="approach-row"><span class="eyebrow">0{i}</span><h3>{e(a.get("title"))}</h3><p>{e(a.get("text"))}</p></article>' for i,a in enumerate(find_all(records,'approach'),1))
    steps=''.join(f'<li><span class="eyebrow">STEP 0{i}</span><h3>{e(s.get("title"))}</h3><p>{e(s.get("text"))}</p></li>' for i,s in enumerate(find_all(records,'step'),1))
    faqs=''.join(f'<details><summary>{e(f.get("question"))}<span aria-hidden="true">＋</span></summary><p>{e(f.get("answer"))}</p></details>' for f in find_all(records,'faq'))
    events=''.join(f'<article class="event-entry" id="{p.get("image")}"><figure>{image(p.get("image"),p.get("title"))}</figure><div><p class="eyebrow">{e(" / ".join(p.all("tag")))}</p><h3>{e(p.get("title"))}</h3><h4>{e(p.get("catch"))}</h4>{paras(p.all("text"))}<p class="detail-role">ROLE / {e(p.get("role"))}</p></div></article>' for p in programs[1:])
    return page_intro('Speaking & Workshop','Speaking<span class="serif">& Workshop.</span>','生成AIと、ものづくりのあいだをつなぐ。講演・実演・体験を通じて、自分のアイデアを形にする一歩を届けます。') + f'''<section class="speaking-intro wrap has-lecture-photo" id="event-01">{lecture_visual()}<div class="lecture-intro-copy"><p class="eyebrow">VIBE CODING INSTRUCTOR</p><h2>{'<br>'.join(map(e,speaking.all('headline')))}</h2>{paras(speaking.all('text'))}<p class="detail-role">担当内容 / {e(programs[0].get('role'))}</p>{link('contact.html?type=speaking','講演・ワークショップを相談する','button')}</div>{lecture_visual(secondary=True)}</section>
<section class="section dark"><div class="wrap">{section_head('01','PROGRAM IDEAS','こんなテーマで、<br>お話しできます。','<p>以下はご相談いただけるテーマ例です。目的・参加者・時間に合わせて構成します。</p>')}{topics()}</div></section>
<section class="section wrap">{section_head('02','APPROACH','大切にしていること。')}{approach}</section>
<section class="section soft"><div class="wrap">{section_head('03','HOW WE WORK','ご相談から、実施まで。')}<ol class="steps">{steps}</ol></div></section>
<section class="section wrap">{section_head('04','QUESTIONS','よくあるご質問。')}<div class="faq">{faqs}</div></section>
<section class="section wrap event-archive">{section_head('05','OTHER ACTIVITIES','作品を、直接届ける場。','<p>講演活動のほか、展示やイベントでの発信にも取り組んでいます。</p>')}{events}</section>{cta()}'''

def works_page():
    filters=''.join(f'<button type="button" data-filter="{e(key)}" aria-pressed="{"true" if key == "all" else "false"}">{e(label)}</button>' for key,label,_ in find(records,'filter').pairs('item', n=3))
    return page_intro('Works','Selected<span class="serif">& collected.</span>',find(records,'works').get('lead'))+f'''<section class="wrap works-catalog"><div class="filters" role="group" aria-label="作品カテゴリー">{filters}</div><p class="result-count" aria-live="polite">10 PROJECTS</p><div class="project-grid">{''.join(card(w,i,True) for i,w in enumerate(works,1))}</div><div class="project-details">{''.join(detail_block(w) for w in works)}</div></section><dialog class="modal" aria-label="作品詳細"><button class="modal-close" type="button" aria-label="詳細を閉じる">Close ×</button><div class="modal-content"></div></dialog>{cta()}'''

def about_page():
    fields=''.join(f'<li><span>0{i}</span><div><h3>{e(f.get("name"))}</h3><p>{e(f.get("text"))}</p></div></li>' for i,f in enumerate(find_all(records,'field'),1))
    return page_intro('About','Making things.<span class="serif">Sharing ideas.</span>','イラスト、デザイン、Web。そして、つくる楽しさを伝えること。')+f'''<section class="profile wrap"><figure>{image('about-main','福山いずみのプロフィール写真',eager=True)}<figcaption>BASED IN OSAKA, JAPAN</figcaption></figure><div><p class="eyebrow">CREATOR / VIBE CODING INSTRUCTOR</p><h2>福山 いずみ<span>Izumi Fukuyama</span></h2><p class="profile-education">大阪芸術大学 デザイン学科卒</p>{paras(about.all('text'))}<blockquote>{e(about.get('quote'))}</blockquote>{paras(about.all('text_after'))}{link('event.html','講演・ワークショップについて')}<a class="profile-instagram" href="{e(site.get('instagram'))}" target="_blank" rel="noopener noreferrer">Instagram / @panda_love_izumi ↗</a></div></section><section class="section wrap">{section_head('01','FIELDS','表現の方法は、ひとつじゃない。')}<ul class="fields">{fields}</ul></section>{cta()}'''

def contact_page():
    email=site.get('email')
    valid=email and email != 'your@example.com'
    action=site.get('form_action')
    attrs=f'action="{e(action)}" method="post"' if action else f'action="mailto:{e(email)}" method="post" enctype="text/plain" data-mail-form data-mail-to="{e(email if valid else "")}"'
    options=['講演・登壇のご相談','ワークショップ・講座のご相談']+[o for o in find(records,'contact').all('option') if o not in ['講演・登壇のご相談','ワークショップ・講座のご相談']]
    option_html=''.join(f'<option>{e(o)}</option>' for o in options)
    contact_link=f'<a class="email-link" href="mailto:{e(email)}">{e(email)} ↗</a>' if valid else '<p>お問い合わせ窓口を準備しています。</p>'
    return page_intro('Contact','Let’s make<span class="serif">something happen.</span>','講演・ワークショップ、イラスト、デザイン、Web制作のご相談を承っています。')+f'''<section class="contact-layout wrap"><aside><p class="eyebrow">START A CONVERSATION</p><h2>まずは、お話を<br>聞かせてください。</h2><p>目的や内容がまだ具体的に決まっていない段階でも、お気軽にご連絡ください。</p>{contact_link}<div class="contact-guide"><h3>講演・ワークショップのご相談</h3><p>開催の目的、対象者、希望時期、場所・実施形式、ご予算など、決まっている範囲でお知らせください。</p><h3>制作のご相談</h3><p>制作内容、用途、ご希望の納期、ご予算などをお知らせいただくと、ご案内がスムーズです。</p></div></aside><form class="form" {attrs}><label for="f-name">お名前 <span>必須</span></label><input id="f-name" name="name" autocomplete="name" required><label for="f-company">会社名・団体名 <span>任意</span></label><input id="f-company" name="company" autocomplete="organization"><label for="f-email">メールアドレス <span>必須</span></label><input id="f-email" name="email" type="email" autocomplete="email" required><label for="f-type">ご相談の内容 <span>必須</span></label><select id="f-type" name="type" required><option value="">選択してください</option>{option_html}</select><label for="f-message">お問い合わせ内容 <span>必須</span></label><textarea id="f-message" name="message" rows="7" required placeholder="ご相談の背景や、ご希望をお聞かせください。"></textarea><p class="form-note"><a href="privacy.html">プライバシーポリシー</a>をご確認のうえ、ご連絡ください。</p>{'<p class="form-note">入力内容をお使いのメールアプリに引き継ぎます。メールアプリで内容をご確認のうえ、送信してください。</p>' if not action else ''}<button class="button" type="submit">{'送信する' if action else 'メールを作成する'} {arrow()}</button><p class="form-feedback" role="status" hidden></p></form></section>'''

def privacy_page():
    privacy=find(records,'privacy')
    body=''; in_list=False
    for key,value in privacy.items:
        if key == 'li':
            if not in_list: body+='<ul>';in_list=True
            body+='<li>'+rich(value)+'</li>'
        else:
            if in_list: body+='</ul>';in_list=False
            if key in ('h2','p'): body+=f'<{key}>{rich(value)}</{key}>'
    if in_list: body+='</ul>'
    updated=privacy.get('updated')
    if updated and '未記入' not in updated: body+='<p>'+e(updated)+'</p>'
    return page_intro('Privacy policy','Privacy<span class="serif">policy.</span>','個人情報の取り扱いについて')+'<article class="prose wrap">'+body+'</article>'

def build():
    pages={'index':home,'event':speaking_page,'works':works_page,'about':about_page,'contact':contact_page,'privacy':privacy_page}
    catalog = Catalog()
    ui_copy = catalog.ui()
    generated = {}
    for name, render in pages.items():
        meta=find(records,'page',name)
        url=urljoin(base,'' if name == 'index' else name+'.html')
        html=f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(meta.get('title'))}</title><meta name="description" content="{e(meta.get('description'))}"><link rel="canonical" href="{e(url)}"><meta property="og:type" content="website"><meta property="og:title" content="{e(meta.get('title'))}"><meta property="og:description" content="{e(meta.get('description'))}"><meta property="og:url" content="{e(url)}"><meta property="og:locale" content="ja_JP"><meta property="og:image" content="{e(urljoin(base, 'images/web/works-01.jpg'))}"><meta name="theme-color" content="#f4f4f0"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{asset('assets/css/style.css')}"><script src="{asset('assets/js/main.js')}" defer></script></head><body id="top" class="page-{name}">{nav(name)}<main id="main">{render()}</main>{footer()}</body></html>'''
        html = catalog.render(html, name)
        payload = json.dumps(ui_copy, ensure_ascii=False).replace('<', '\\u003c')
        html = html.replace('</head>', '<script type="application/json" id="site-ui-copy">' + payload + '</script></head>')
        generated[name] = html
    catalog.save()
    for name, html in generated.items():
        (Path(ROOT)/(name+'.html')).write_text(html,encoding='utf-8')
        print('Built',name+'.html')

if __name__ == '__main__':
    build()
