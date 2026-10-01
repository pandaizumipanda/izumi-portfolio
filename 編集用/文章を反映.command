#!/bin/zsh
cd -- "${0:A:h}/.." || exit 1
if /usr/bin/python3 tools/build_site.py; then
  print '\n文章をサイトに反映しました。ブラウザを再読み込みしてください。'
else
  print '\n反映できませんでした。上のエラーを確認してください。'
fi
read -r '?Enterキーで閉じます。'
