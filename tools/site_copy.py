"""All rendered copy lives in one owner-editable UTF-8 text file.

IDs depend on original template text, not its edited value. Existing edits are
preserved when the generator discovers new text. HTML markup is never editable.
"""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
COPY_FILE = ROOT / '編集用' / 'サイトの文章.txt'
PAGE_NAMES = {'index':'ホーム', 'event':'講演・ワークショップ', 'works':'制作実績',
              'about':'プロフィール', 'contact':'お問い合わせ', 'privacy':'プライバシーポリシー'}
AREAS = {'header':'ヘッダー', 'footer':'フッター', 'hero-display':'写真上の大きな英字',
         'hero-topline':'写真上部の肩書き', 'hero-bottom':'写真下部の案内',
         'hero-copy':'ホーム冒頭の紹介', 'speaking-section':'講演紹介',
         'work-section':'ピックアップ作品', 'about-section':'プロフィール紹介',
         'contact-band':'下部の依頼案内', 'page-intro':'ページ冒頭',
         'speaking-intro':'講座写真と紹介文', 'topic':'講演テーマ',
         'approach-row':'大切にしていること', 'steps':'依頼の流れ',
         'faq':'よくあるご質問', 'event-entry':'展示活動',
         'filters':'作品の絞り込み', 'project-caption':'作品カード',
         'project-detail':'作品の詳細', 'profile':'プロフィール本文',
         'fields':'活動分野', 'contact-layout':'お問い合わせ本文', 'form':'入力フォーム',
         'contact-guide':'ご相談の案内', 'prose':'ポリシー本文',
         'lecture-photo':'講座写真', 'about-home':'プロフィール紹介'}
ROLES = {'h1':'大見出し', 'h2':'見出し', 'h3':'小見出し', 'h4':'小見出し',
         'p':'本文', 'a':'リンク・ボタン', 'button':'ボタン', 'label':'入力項目名',
         'option':'選択肢', 'summary':'質問', 'figcaption':'写真の説明',
         'title':'ブラウザのタイトル', 'li':'箇条書き', 'blockquote':'引用'}
UI_DEFAULTS = {
    'count_one': ('作品一覧：絞り込み後の件数（{count} は件数に置き換わります）', '{count} PROJECT'),
    'count_many': ('作品一覧：絞り込み後の件数（{count} は件数に置き換わります）', '{count} PROJECTS'),
    'mail_unset': ('お問い合わせ：送信先が未設定のときの案内', 'お問い合わせ先を準備しています。'),
    'mail_help': ('お問い合わせ：メール作成ボタンを押した後の案内', 'メールアプリで内容を確認し、送信してください。開かない場合は、ページに記載のメールアドレスへ直接ご連絡ください。'),
    'mail_subject': ('作成されるメールの件名（{type}＝相談種別、{name}＝名前）', '【お問い合わせ】{type} / {name}'),
    'mail_body': ('作成されるメールの本文（{...} は入力内容です）', 'お名前：{name}\n会社名・団体名：{company}\nメールアドレス：{email}\nご相談の内容：{type}\n\n{message}'),
}

def copy_id(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

class Catalog:
    def __init__(self):
        self.values = {}
        self.entries = {}
        if COPY_FILE.exists():
            source = COPY_FILE.read_text(encoding='utf-8')
            pattern = r'^【文言 ([a-f0-9]{16})】\n使用箇所：[^\n]*\n本文：\n(.*?)\n【ここまで】'
            matches = list(re.finditer(pattern, source, flags=re.M | re.S))
            if len(matches) != source.count('【文言 '):
                raise ValueError('サイトの文章.txt の区切りを確認してください（【文言 ...】／使用箇所：／本文：／【ここまで】）。')
            for m in matches:
                if m[1] in self.values: raise ValueError('文言IDが重複しています: '+m[1])
                self.values[m[1]] = m[2]

    def text(self, original, location):
        key = copy_id(original)
        item = self.entries.setdefault(key, {'original':original, 'locations':[]})
        if location not in item['locations']: item['locations'].append(location)
        return self.values.get(key, original)

    def render(self, html, page):
        parser = CopyHTML(self, PAGE_NAMES[page])
        parser.feed(html)
        return ''.join(parser.output)

    def ui(self):
        return {key:self.text(value, '動作時の文章 > '+location)
                for key,(location,value) in UI_DEFAULTS.items()}

    def save(self):
        # Avoid rewriting the user's file on normal builds. Append only new copy.
        missing = [(key,item) for key,item in self.entries.items() if key not in self.values]
        if not missing: return
        first = not COPY_FILE.exists()
        COPY_FILE.parent.mkdir(exist_ok=True)
        header = '''# サイトの文章 — この1ファイルで表示文章を編集できます
# 「本文：」と「【ここまで】」の間だけを書き換えて保存してください。
# 見出し・本文・ボタン・画像説明・検索/SNS用文章・フォーム案内を収録しています。
# 同じ文章を複数箇所で使う場合は1項目にまとめ、使用箇所を併記しています。
# 本文は改行できます。HTMLタグを記入する必要はありません。
# 文言ID、使用箇所、区切りの行は変更しないでください。本文を空にすると非表示になります。
# {count} や {name} などは動的に入る値です。残して編集してください。
# 保存したら「文章を反映.command」をダブルクリックし、ブラウザを再読み込みします。
# 公開サイトの更新には、その後GitHubへの反映が必要です。
# content.txt は構造・画像・元データ用です。表示文章はこのファイルを優先します。

'''
        with COPY_FILE.open('a', encoding='utf-8') as f:
            if first:f.write(header)
            else:f.write('\n# 新しく追加された文言\n\n')
            for key,item in missing:
                f.write('【文言 '+key+'】\n使用箇所：'+' ／ '.join(item['locations'])+'\n本文：\n'+item['original']+'\n【ここまで】\n\n')

class CopyHTML(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self, catalog, page):
        super().__init__(convert_charrefs=True)
        self.catalog=catalog; self.page=page; self.stack=[]; self.output=[]

    def location(self, attribute=None):
        areas=[]
        for tag,attrs in self.stack:
            for cls in attrs.get('class','').split():
                if cls in AREAS and AREAS[cls] not in areas:areas.append(AREAS[cls])
            if tag in ('header','footer') and AREAS[tag] not in areas:areas.append(AREAS[tag])
            if attrs.get('id','').startswith(('works-','event-')):areas.append(attrs['id'])
        role=attribute or next((ROLES[t] for t,_ in reversed(self.stack) if t in ROLES),'表示テキスト')
        return ' > '.join([self.page]+areas+[role])

    def handle_decl(self, decl):self.output.append('<!'+decl+'>')
    def handle_comment(self, text):self.output.append('<!--'+text+'-->')
    def handle_starttag(self, tag, attrs):
        a=dict(attrs);self.stack.append((tag,a));out=[]
        # Preserve option values even when their visible labels are edited.
        for key,value in attrs:
            if value is not None and (key in ('alt','aria-label','placeholder','title') or
                (tag=='meta' and key=='content' and (a.get('name')=='description' or a.get('property') in ('og:title','og:description')))):
                role={'alt':'画像の説明（代替テキスト）','aria-label':'読み上げ用ラベル','placeholder':'入力欄の例文','title':'補足説明'}.get(key,'検索・SNS用の説明')
                value=self.catalog.text(value,self.location(role))
            out.append(key if value is None else key+'="'+escape(value,quote=True)+'"')
        self.output.append('<'+tag+(' '+' '.join(out) if out else '')+'>')
        if tag in self.VOID:self.stack.pop()
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        self.output.append('</'+tag+'>')
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:del self.stack[i:];break
    def handle_data(self,data):
        if not data.strip() or any(t in ('script','style') for t,_ in self.stack):
            self.output.append(data);return
        raw=data.strip()
        # Decorative symbols and ordinal numbers are layout, not prose.
        if not re.search(r'[A-Za-z\u3040-\u30ff\u3400-\u9fff]',raw):self.output.append(escape(data));return
        if any('result-count' in attrs.get('class','').split() for _,attrs in self.stack):
            count = re.search(r'\d+', raw).group()
            value = self.catalog.text(UI_DEFAULTS['count_many'][1], '動作時の文章 > '+UI_DEFAULTS['count_many'][0]).replace('{count}', count)
        else:
            value=self.catalog.text(raw,self.location())
        content=escape(value,quote=False)
        if not any(t in ('title','option') for t,_ in self.stack):content=content.replace('\n','<br>')
        self.output.append(data[:len(data)-len(data.lstrip())]+content+data[len(data.rstrip()):])
