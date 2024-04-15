import click

import simple_config_sync


@click.group()
def cli():
    pass


@cli.command()
def version():
    click.echo(simple_config_sync.__version__)


@cli.command()
def tui():
    simple_config_sync.core.run_tui()
