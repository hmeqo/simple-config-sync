from . import config


def sync():
    for op in config.options.values():
        op.sync()
    config.make_lock_file()
    config.load()


def uninstall():
    for op in config.options.values():
        op.uninstall()
    config.make_lock_file()
    config.load()
