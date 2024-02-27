def run_tui():
    from . import config
    from .tui import SimpleConfigSyncApp

    config.load()
    app = SimpleConfigSyncApp()
    app.run()
