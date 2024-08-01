import importlib.metadata
from pathlib import Path

import click

import simple_config_sync

CONFIG_SYNC_TEMPLATE = """[options.neovim]
tags = ["Editor"]
links = [{ source = "dotfiles/a", target = "config/a" }]
depends = { system = ["neovim"] }

[options.neovide]
description = "Gui for neovim."
links = [{ source = "dotfiles/b", target = "config/b" }]
depends = { system = ["neovide"], item = ["neovim"] }
"""


@click.group()
def cli():
    pass


@cli.command()
def version():
    click.echo(importlib.metadata.version("simple_config_sync"))


@cli.command()
def tui():
    simple_config_sync.core.run_tui()


@cli.command()
def init():
    conf_path = Path("config-sync.toml")
    if conf_path.exists():
        click.echo(f"Config file already exists: {conf_path}")
        return
    conf_path.write_text(CONFIG_SYNC_TEMPLATE)
