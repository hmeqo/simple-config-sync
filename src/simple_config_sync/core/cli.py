from pathlib import Path

import click

import simple_config_sync

CONFIG_SYNC_TEMPLATE = """[options.a]
group = "default group"
description = "A config file."
links = [{ source = "./dotfiles/a", target = "config/a" }]
depends = { system = ["neovim"], group = ["b"] }
"""


@click.group()
def cli():
    pass


@cli.command()
def version():
    click.echo(simple_config_sync.__version__)


@cli.command()
def tui():
    simple_config_sync.core.run_tui()


@cli.command()
def init():
    Path("config-sync.toml").write_text(CONFIG_SYNC_TEMPLATE)
