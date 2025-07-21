import shutil
from fastcore.all import Path
from fastcore.xtras import globtastic
from datetime import datetime
from .logging import get_logger
from .cfg import cfg, get_log_pth

__all__ = ['create_backup', 'clean_dates', 'run_backup', 'compress', 'clone', 'get_date', 'conv_date']
def get_date(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def conv_date(d): return datetime.strptime(d, '%Y%m%d_%H%M%S') if isinstance(d, str) else d
lgr = get_logger(get_log_pth('backup'))
info,err,warn=lgr.info,lgr.error,lgr.warning

def create_backup(src,dest_dir,dry_run=False,**kwargs):
    sp = Path(src)
    dp = Path(dest_dir) / get_date()
    if not dry_run: dp.mkdir(parents=True, exist_ok=True)
    if sp.is_file():files_to_copy = [sp]
    else: files_to_copy = globtastic(sp,func=Path, **kwargs)
    for f in files_to_copy:
        if f.is_file():
            df = dp / f.relative_to(sp)
            if not dry_run: df.parent.mkdir(parents=True, exist_ok=True)
            try: print(f'Copy from {f} to {df}') if dry_run else shutil.copy2(f, df)
            except Exception as e: warn(f"Failed to copy {f}: {e}")

def clean_dates(dates, now=None, max_ages=(2, 14, 60), k=5):
    now, clean = now or datetime.now(), []
    dates.sort()
    for a in max_ages:
        lt_max = [d for d in dates if (now - conv_date(d)).days < a]
        if lt_max: clean.append(lt_max[0])
    clean.extend(dates[-k:])  # Keep the newest 5
    return sorted(set(clean))

def run_backup(src=cfg.data_root,dest=cfg.backup_path,max_ages= "2,14,60",dry_run=False,
               recursive=True,symlinks=True,file_glob:str=None,file_re:str=None,
               folder_re:str=None,skip_file_glob:str=None,skip_file_re:str=None,
               skip_folder_re:str=None):
    """Run backup and cleanup old files. Takes globtastic args."""
    # Set up logging
    try:
        create_backup(src,dest,dry_run,recursive=recursive,symlinks=symlinks,file_glob=file_glob,file_re=file_re,
                      folder_re=folder_re, skip_file_glob=skip_file_glob,skip_file_re=skip_file_re,skip_folder_re=skip_folder_re)
        info(f"Backup created: {src} -> {dest}")
    except Exception as e: err(f"Backup failed: {str(e)}", exc_info=True)
    finally: clean_old_backups(dest, dry_run, max_ages)

def clean_old_backups(dest, dry_run, max_ages):
    max_ages = [int(age.strip()) for age in max_ages.split(',')]
    bkps = [d.name for d in Path(dest).iterdir() if d.is_dir()]
    to_keep = clean_dates(bkps, max_ages=max_ages)
    for bkp in bkps:
        if bkp in to_keep: continue
        try: shutil.rmtree(Path(dest) / bkp) if dry_run else print('Remove', Path(dest) / bkp); info(f"Removed old backup: {bkp}")
        except Exception as e: err(f"Removing old backup failed: {str(e)}", exc_info=True)


def compress(src, dest=None, dated=True):
    """Compress folder `src` to `src.tar.gz`"""
    src = Path(src)
    if not dest: dest = src
    if src.is_file(): src = [src]
    out = Path(dest).with_name(f'{src.stem}{'_'+get_date() if dated else ''}.tar.gz')
    import tarfile
    with tarfile.open(out, 'w:gz') as tar: tar.add(src, arcname=src.name)
    return out

def clone(src=cfg.static, remote=cfg.app_nm, bucket=cfg.app_nm.lower(), sync=True, zip=True, dated=False):
    """Sync or copy a directory to a remote bucket using rclone. optionally zip if copying."""
    src=Path(src)
    if not src.exists(): err(f'Source path {src} does not exist.'); return
    from rclone_python import rclone
    if not rclone.is_installed(): info('rclone not installed.');return
    if not rclone.check_remote_existing(remote):
        try: rclone.create_remote(remote, remote_type=cfg.rc_typ, **cfg.rc_remote); info(f'Created remote: {remote}')
        except Exception as e: err(f'Failed to create remote: {remote}: {e}'); return
    if not remote.endswith(':'): remote = remote+':'
    d = f'{remote}{bucket}/{src.stem if src.is_dir() else ''}/'
    try: rclone.mkdir(d); info(f'Created bucket: {d} on remote: {remote}')
    except Exception as e: err(f'Failed to create bucket {d} on remote {remote}: {e}'); return
    if sync:
        try: rclone.sync(str(src.absolute()), d)
        except Exception as e: err(f'Failed to sync {src} to {d} on remote {remote}: {e}')
    else:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            if zip:src=compress(src, Path(td), dated);
            info(f'Compressing {src} before copying to {d}')
            try: rclone.copy(str(src.absolute()), d, show_progress=True)
            except: err(f'Failed to copy {src} to {d} on remote {remote}')