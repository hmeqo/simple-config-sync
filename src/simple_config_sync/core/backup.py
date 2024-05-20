import shutil
from pathlib import Path

import mmh3

BACKUP_DIR = Path("backup")

if not BACKUP_DIR.exists():
    BACKUP_DIR.mkdir()


def to_backup_path(fp: Path) -> Path:
    return (
        BACKUP_DIR
        / f"{fp.name}-{mmh3.hash64(str(fp.absolute().relative_to(Path('~').expanduser())), signed=False)[0]:x}"
    )


def backup(fp: Path) -> None:
    if not fp.exists():
        return
    shutil.move(fp, to_backup_path(fp))


def restore(fp: Path) -> None:
    path = to_backup_path(fp)
    if not path.exists():
        return
    shutil.move(path, fp)
