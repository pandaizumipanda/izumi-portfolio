"""macOS sips で表示用JPEGを生成。原本のPNGは変更しません。"""
from pathlib import Path
import subprocess
import shutil

ROOT = Path(__file__).resolve().parent.parent
out = ROOT / 'images' / 'web'
out.mkdir(exist_ok=True)
for name in ['about-main'] + [f'works-{n:02}' for n in range(1, 11)] + ['event-02', 'event-03']:
    src = ROOT / 'images' / f'{name}.png'
    dest = out / f'{name}.jpg'
    # This original has a .png extension but is already JPEG. Preserve its bytes;
    # sips produced a black image when resizing/re-encoding it.
    if name == 'works-01' and src.exists():
        shutil.copyfile(src, dest)
        print(f'{name}: 元のJPEGをそのまま使用')
        continue
    if src.exists() and (not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime):
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', '-Z', '1600', str(src), '--out', str(dest)], check=True, capture_output=True)
        print(f'{name}: {src.stat().st_size // 1024} KB → {dest.stat().st_size // 1024} KB')
