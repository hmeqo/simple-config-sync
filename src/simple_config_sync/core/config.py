import os
from copy import deepcopy
from functools import cached_property
from pathlib import Path
from typing import Literal, Protocol

import toml

from .backup import backup, restore

Status = Literal["added", "modified", "deleted", ""]


class OptionProtocol(Protocol):
    def sync(self) -> None: ...
    def uninstall(self, clean: bool = False) -> None: ...


class Link(OptionProtocol):
    def __init__(self, d: dict) -> None:
        self.d = d

    def __eq__(self, value: "Option") -> bool:
        return self.d == value.d

    def sync(self):
        if not self.source.exists():
            raise FileNotFoundError(f"Source file not found: {self.source}")
        self.clean_target()
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.symlink_to(self.source.resolve(), self.source.is_dir())

    def uninstall(self) -> None:
        if not self.linked:
            return
        self.target.unlink()
        restore(self.target)

    def clean_target(self):
        if not self.target.exists():
            if self.target.is_symlink():
                self.target.unlink()
            return
        backup(self.target)

    @property
    def linked(self) -> bool:
        if not (self.target.is_symlink() and self.target.exists()):
            return False
        return self.source.resolve() == self.target.readlink()

    @cached_property
    def source(self) -> Path:
        return Path(os.path.expandvars(self.d.get("source", ""))).expanduser()

    @cached_property
    def target(self) -> Path:
        return Path(os.path.expandvars(self.d.get("target", ""))).expanduser()


class Option(OptionProtocol):
    def __init__(self, name: str, d: dict | None) -> None:
        self.name = name
        self.d = d or {}

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __bool__(self) -> bool:
        return bool(self.d)

    def __eq__(self, value: "Option") -> bool:
        return self.name == value.name

    def sync(self) -> None:
        for link in self.links:
            link.sync()

    def uninstall(self) -> None:
        for link in self.links:
            link.uninstall()

    @property
    def group(self) -> str:
        return self.d.get("group", "")

    @property
    def description(self) -> str:
        return self.d.get("description", "")

    @property
    def links(self) -> list[Link]:
        return [Link(i) for i in self.d.get("links", [])]

    @property
    def depends(self) -> dict[str, list]:
        return self.d.get("depends", {})

    @property
    def synced(self) -> bool:
        return self.d.get("synced", False)

    @synced.setter
    def synced(self, value: bool) -> None:
        self.d["synced"] = value

    @property
    def status(self) -> Status:
        return self.d.get("status", "")


class SyncOp(Option, OptionProtocol):
    def __init__(self, name: str, op: dict | None = None, lock_op: dict | None = None):
        assert op or lock_op
        self.op = Option(name, op)
        self.lock_op = Option(name, lock_op)
        super().__init__(name, self._sync_op())

    def _sync_op(self) -> dict:
        synced: bool = bool(self.op and (self.lock_op and self.lock_op.synced))
        if self.status == "deleted":
            return deepcopy(self.lock_op.d) | {"synced": synced}
        return deepcopy(self.op.d) | {"synced": synced}

    def sync(self) -> None:
        if not self.synced:
            self.uninstall()
            return
        self.lock_op.uninstall()
        self.op.sync()
        self.synced = True

    def uninstall(self) -> None:
        self.lock_op.uninstall()
        self.synced = False

    @property
    def status(self) -> Status:
        if not self.op:
            return "deleted"
        if not self.lock_op:
            return "added"
        if self.op.links != self.lock_op.links:
            return "modified"
        return ""

    @status.setter
    def status(self, value: Status):
        self.d["status"] = value


class Config:
    def __init__(self) -> None:
        self.path = Path("config-sync.toml")
        self.lock_path = Path("config-sync.lock")
        self.opt_names: list[str] = []
        self.lock_opt_names: list[str] = []
        self.opts: list[SyncOp] = []

    def load(self) -> None:
        with open(self.path) as f:
            d = toml.load(f)
            opts: dict = d.get("options", {})
        if self.lock_path.exists():
            with open(self.lock_path) as f:
                lock_d = toml.load(f)
            lock_opts: dict = lock_d.get("options", {})
        else:
            lock_opts = {}
        self.opt_names = list(opts.keys())
        self.lock_opt_names = list(lock_opts.keys())
        self.opts.clear()
        self.opts.extend(SyncOp(i, opts[i], lock_opts.get(i)) for i in opts)
        self.opts.extend(SyncOp(i, None, lock_opts[i]) for i in lock_opts if i not in opts)

    def lock(self) -> None:
        with open(self.lock_path, "w") as f:
            toml.dump({"options": {i.name: i.d for i in self.opts if i.op}}, f)

    def sync(self) -> None:
        for op in filter(lambda x: x.status == "deleted", self.opts):
            op.sync()
        for op in filter(lambda x: x.status != "deleted", self.opts):
            op.sync()
        self.lock()
        self.load()

    def uninstall(self) -> None:
        for op in self.opts:
            if op.name not in self.lock_opt_names:
                continue
            op.uninstall()
        self.lock()
        self.load()


config = Config()
