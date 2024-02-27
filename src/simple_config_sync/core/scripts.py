from . import config


def sync():
    for op in config.options.values():
        if op.status == 'deleted' or not op.synced:
            op.uninstall()
        else:
            op.install()
    config.make_lock_file()
    config.load()


def uninstall():
    for op in config.options.values():
        op.uninstall()
    config.make_lock_file()
    config.load()
