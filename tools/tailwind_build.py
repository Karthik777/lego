'''Compile the hora block's Tailwind stylesheet.

The page came from a standalone file that pulled `cdn.tailwindcss.com` into the head. That
script is a compiler: every visitor downloaded ~400KB of JIT, which then scanned the DOM
and generated the stylesheet in the browser, on every load. Compiled here instead, the same
page ships a few KB of CSS behind the immutable mount and a content-hashed ?v=, and the
head has no third-party origin left in it.

`hora.js` is scanned alongside the markup because the hora cards are built at runtime from
template literals — every class the grid uses appears only there. All of them are literal
strings, which is what Tailwind's extractor needs; a class assembled from fragments at
runtime would not survive this.

Run after changing page.html, hora.js or hora.src.css, then commit lego/hora/hora.css:

    uv run python tools/tailwind_build.py

Needs node (npx) at build time only.
'''
import subprocess, sys
from pathlib import Path

TW = 'tailwindcss@3.4.17'
BLOCK = Path('lego/hora')
SRC, OUT = BLOCK / 'hora.src.css', BLOCK / 'hora.css'
# The content list lives in the config rather than in repeated --content flags: the CLI
# keeps only the last of those, which silently drops every class that is in page.html and
# nowhere else.
CFG = Path('tools/tailwind.hora.js')

def build():
    if not SRC.exists(): sys.exit(f'missing {SRC}')
    cmd = ['npx', '--yes', TW, '-c', str(CFG), '-i', str(SRC), '-o', str(OUT), '--minify']
    print(' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr or r.stdout)
    print(r.stderr.strip() or r.stdout.strip())
    print(f'  {OUT}  {OUT.stat().st_size/1024:.1f}KB')

if __name__ == '__main__': build()
