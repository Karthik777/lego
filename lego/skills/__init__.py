import shutil, sys
from fastcore.all import Path

__all__ = ['install', 'install_cli']

_here = Path(__file__).parent

# Skills bundled here: lego + tools that don't ship their own skill.
# kosha, vpseasy, litesearch ship their own — install via:
#   k.sync()           (kosha)
#   vpseasy-skill .    (vpseasy, if available)
#   litesearch-skill . (litesearch, if available)
_bundled = ['SKILL.md', 'dockeasy.md', 'cfeasy.md', 'gheasy.md']

def _install_one(src: Path, dest: Path, name: str):
    dst = dest / '.claude' / 'skills' / name
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst / 'SKILL.md')
    print(f'installed → {dst}/SKILL.md')

def install(dest='.'):
    dest = Path(dest)
    for fname in _bundled:
        name = fname.replace('.md', '').replace('SKILL', 'lego')
        _install_one(_here / fname, dest, name)

def install_cli():
    dest = sys.argv[1] if len(sys.argv) > 1 else '.'
    install(dest)
