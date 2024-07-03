import shutil
from pathlib import Path

import mmh3

BACKUP_DIR = Path("backup")

if not BACKUP_DIR.exists():
    BACKUP_DIR.mkdir()


def to_backup_path(fp: Path) -> Path:
    hash_num = mmh3.hash64(str(fp.absolute().relative_to(Path("~").expanduser())), signed=False)[0]
    return BACKUP_DIR / f"{fp.name}-{hash_num:x}"


def backup(fp: Path) -> None:
    backup_path = to_backup_path(fp)
    if backup_path.exists():
        if backup_path.is_dir():
            shutil.rmtree(backup_path)
        else:
            backup_path.unlink()
    shutil.move(fp, backup_path)


def restore(fp: Path) -> None:
    path = to_backup_path(fp)
    if not path.exists():
        return
    shutil.move(path, fp)
