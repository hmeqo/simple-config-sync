import os
import shutil
from copy import deepcopy
from functools import cached_property
from pathlib import Path
from typing import Literal

import toml

Status = Literal["added", "modified", "deleted", ""]


class Link:
    def __init__(self, d: dict) -> None:
        self.d = d

    def __eq__(self, value: "Option") -> bool:
        return self.d == value.d

    def uninstall(self) -> None:
        if not self.target.exists():
            return
        if self.target.is_symlink():
            self.target.unlink()

    def clean_target(self) -> None:
        if not self.target.exists():
            return
        if self.target.is_symlink() or self.target.is_file():
            self.target.unlink()
        else:
            shutil.rmtree(self.target)

    def sync(self):
        if not self.source.exists():
            raise FileNotFoundError(f"Source file not found: {self.source}")
        if self.target.exists():
            self.clean_target()
        self.target.symlink_to(self.source.resolve(), self.source.is_dir())

    @property
    def linked(self) -> bool:
        if not self.target.exists() or not self.target.is_symlink():
            return False
        return self.source.resolve() == self.target.readlink()

    @cached_property
    def source(self) -> Path:
        return Path(os.path.expandvars(self.d.get("source", ""))).expanduser()

    @cached_property
    def target(self) -> Path:
        return Path(os.path.expandvars(self.d.get("target", ""))).expanduser()


class Option:
    def __init__(self, d: dict | None) -> None:
        self.d = d or {}

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.description})"

    def __bool__(self) -> bool:
        return bool(self.d)

    @property
    def name(self) -> str:
        return self.d.get("name", "")

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


class SyncOp(Option):
    def __init__(self, op: dict | None = None, lock_op: dict | None = None):
        assert op or lock_op
        self.op = Option(op)
        self.lock_op = Option(lock_op)
        super().__init__(self._sync_op())

    def _sync_op(self):
        synced = self.op and (self.lock_op and self.lock_op.synced)
        if self.status == "deleted":
            return deepcopy(self.lock_op.d) | {"synced": synced}
        return deepcopy(self.op.d) | {"synced": synced}

    def sync(self):
        if not self.synced:
            self.uninstall()
            return
        for link in self.lock_op.links:
            link.uninstall()
        for link in self.op.links:
            link.sync()
        self.synced = True

    def uninstall(self):
        for link in self.lock_op.links:
            link.uninstall()
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
        self._opts: list[Option] = []
        self._lock_opts: list[Option] = []
        self.opts: list[SyncOp] = []

    def load(self) -> None:
        with open(self.path) as f:
            d = toml.load(f) or {}
            opts = {i.get("name", ""): i for i in d.get("option", [])}
        if self.lock_path.exists():
            with open(self.lock_path) as f:
                lock_d = toml.load(f) or {}
            lock_opts = {i.get("name", ""): i for i in lock_d.get("option", [])}
        else:
            lock_opts = {}
        self.opts.clear()
        sync_opts = []
        for i in opts:
            sync_opts.append(SyncOp(opts[i], lock_opts.get(i)))
        for i in lock_opts:
            if i not in opts:
                sync_opts.append(SyncOp(None, lock_opts[i]))
        self.opts.extend(sync_opts)

    def lock(self) -> None:
        with open(self.lock_path, "w") as f:
            toml.dump({"option": [i.d for i in self.opts if i.op]}, f)

    def sync(self) -> None:
        for op in filter(lambda x: x.status == "deleted", self.opts):
            op.sync()
        for op in filter(lambda x: x.status != "deleted", self.opts):
            op.sync()
        self.lock()
        self.load()

    def uninstall(self) -> None:
        for op in self.opts:
            op.uninstall()
        self.lock()
        self.load()


config = Config()
