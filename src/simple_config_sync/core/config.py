import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Literal

import toml

Status = Literal['added', 'modified', 'deleted', '']


default_config_path = Path('./config-sync.toml')
default_lock_path = Path('./config-sync.lock')


def load(config_path: Path | None = None, lock_path: Path | None = None) -> None:
    config_path = config_path or default_config_path
    lock_path = lock_path or default_lock_path

    if not config_path.exists():
        raise FileNotFoundError(f'Could not find config file: {config_path}')

    config = toml.load(config_path)
    lock_cfg = toml.load(lock_path) if lock_path.exists() else {}

    ops: dict = config.get('options', {})
    lock_ops: dict = lock_cfg.get('options', {})

    options.clear()
    options.update({k: SyncOp(ops.get(k), lock_ops.get(k)) for k in sorted(set(ops).union(lock_ops))})


def make_lock_file(lock_path: Path | None = None) -> None:
    lock_path = lock_path or default_lock_path

    config = {'options': {}}
    for k, op in options.items():
        if op.status == 'deleted':
            continue
        config['options'][k] = op.d
    with lock_path.open('w') as file:
        toml.dump(config, file)


class Link(dict):
    def install(self):
        if self.linked:
            return
        source = Path(os.path.expandvars(self.source)).expanduser().absolute()
        target = Path(os.path.expandvars(self.target)).expanduser().absolute()
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, source.is_dir())

    def uninstall(self):
        target = Path(self.target)
        if target.exists() and target.is_symlink():
            target.unlink()

    @property
    def source(self) -> str:
        return self.get('source', '')

    @source.setter
    def source(self, value: str):
        self['source'] = value

    @property
    def target(self) -> str:
        return self.get('target', '')

    @target.setter
    def target(self, value: str):
        self['target'] = value

    @property
    def target_exists(self) -> bool:
        return Path(self.target).exists()

    @property
    def linked(self) -> bool:
        target = Path(self.target)
        if not target.exists() or not target.is_symlink():
            return False
        return Path(os.path.expandvars(self.source)).expanduser().absolute() == target.readlink()


class Option:
    def __init__(self, d: dict | None = None):
        self.d = d or {}

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self.description})'

    def __bool__(self) -> bool:
        return bool(self.d)

    @property
    def description(self) -> str:
        return self.d.get('description', '')

    @description.setter
    def description(self, value: str):
        self.d['description'] = value

    @property
    def links(self) -> list[Link]:
        return [Link(i) for i in self.d.get('links', [])]

    @links.setter
    def links(self, value: list[dict]):
        self.d['links'] = value

    @property
    def synced(self) -> bool:
        return self.d.get('synced', True)

    @synced.setter
    def synced(self, value: bool):
        self.d['synced'] = value

    @property
    def status(self) -> Status:
        return self.d.get('status', '')

    @status.setter
    def status(self, value: Status):
        self.d['status'] = value


class SyncOp(Option):
    def __init__(self, op: dict | None = None, lock_op: dict | None = None):
        assert op or lock_op
        self.op = Option(op)
        self.lock_op = Option(lock_op)
        super().__init__(self.sync_lock())
        self.synced = self.lock_op.synced

    def sync_lock(self):
        if self.status == 'deleted':
            return deepcopy(self.lock_op.d)
        return deepcopy(self.op.d)

    def install(self):
        for link in self.lock_op.links:
            link.uninstall()
        for link in self.links:
            link.install()

    def uninstall(self):
        self.status = 'deleted'
        for link in self.lock_op.links:
            link.uninstall()

    @property
    def status(self) -> Status:
        if not self.op:
            return 'deleted'
        if not self.lock_op or self.lock_op.status == 'deleted' or not self.lock_op.synced:
            return 'added'
        if self.op.links != self.lock_op.links:
            return 'modified'
        return ''

    @status.setter
    def status(self, value: Status):
        self.d['status'] = value


options: dict[str, SyncOp] = {}
