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
        source = self.source
        target = self.target
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source.absolute(), source.is_dir())

    def uninstall(self):
        target = self.target
        if target.exists() and target.is_symlink():
            target.unlink()

    @property
    def source(self) -> Path:
        return Path(os.path.expandvars(self.get('source', ''))).expanduser()

    @source.setter
    def source(self, value: Path | str):
        self['source'] = str(value)

    @property
    def target(self) -> Path:
        return Path(os.path.expandvars(self.get('target', ''))).expanduser()

    @target.setter
    def target(self, value: Path | str):
        self['target'] = str(value)

    @property
    def target_exists(self) -> bool:
        target = self.target
        return target.exists() or target.is_symlink()

    @property
    def linked(self) -> bool:
        target = self.target
        if not target.is_symlink():
            return False
        return target.readlink() == self.source.absolute()


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
    def group(self) -> str:
        return self.d.get('group', '')

    @property
    def description(self) -> str:
        return self.d.get('description', '')

    @property
    def links(self) -> list[Link]:
        return [Link(i) for i in self.d.get('links', [])]

    @property
    def synced(self) -> bool:
        return self.d.get('synced', True)

    @synced.setter
    def synced(self, value: bool):
        self.d['synced'] = value

    @property
    def status(self) -> Status:
        return self.d.get('status', '')

    @property
    def dependencies(self) -> list[str]:
        return self.d.get('dependencies', [])


class SyncOp(Option):
    def __init__(self, op: dict | None = None, lock_op: dict | None = None):
        assert op or lock_op
        self.op = Option(op)
        self.lock_op = Option(lock_op)
        super().__init__(self.sync_lock())
        self.synced = self.lock_op.synced if self.lock_op else self.op.synced

    def sync_lock(self):
        if self.status == 'deleted':
            return deepcopy(self.lock_op.d)
        return deepcopy(self.op.d)

    def install(self):
        for link in self.links:
            link.install()

    def uninstall(self):
        self.status = 'deleted'
        for link in self.lock_op.links:
            link.uninstall()

    def sync(self):
        if self.status == 'deleted' or not self.synced:
            self.uninstall()
        else:
            self.install()

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
