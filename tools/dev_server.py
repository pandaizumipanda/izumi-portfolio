# -*- coding: utf-8 -*-
"""
ローカルプレビュー用の簡易サーバー（標準ライブラリのみ）

    python3 tools/dev_server.py            http://localhost:5173/ で表示
    python3 tools/dev_server.py 8000       ポート番号を変える

ブラウザにキャッシュさせない設定にしてあるので、CSSや画像を差し替えたあと
再読み込みするだけで必ず最新の表示になります（公開用サーバーとしては使いません）。
"""

import functools
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        SimpleHTTPRequestHandler.end_headers(self)


def main():
    port = 5173
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    handler = functools.partial(NoCacheHandler, directory=ROOT)
    server = ThreadingHTTPServer(("", port), handler)
    print(u"http://localhost:%d/  （終了は Ctrl+C）" % port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(u"\n終了しました")


if __name__ == "__main__":
    main()
