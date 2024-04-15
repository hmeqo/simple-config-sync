from .cli import cli
from .config import config
from .tui import SimpleConfigSyncApp


def run_tui():
    config.load()
    app = SimpleConfigSyncApp()
    app.run()


def run_cli():
    cli()
