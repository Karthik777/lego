import shutil, sys
from fastcore.all import Path

__all__ = ['install', 'install_cli']

_skill = Path(__file__).parent / 'SKILL.md'

def install(dest='.'):
    dst = Path(dest) / '.claude' / 'skills' / 'lego'
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(_skill, dst / 'SKILL.md')
    print(f'lego skill installed → {dst}/SKILL.md')

def install_cli():
    dest = sys.argv[1] if len(sys.argv) > 1 else '.'
    install(dest)
