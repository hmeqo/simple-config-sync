from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Checkbox, Footer, Header, Static

from .config import Link as _Link
from .config import Option as _Option
from .config import config


class Link(Horizontal):
    def __init__(self, link: _Link, **kwds):
        self.link = link
        super().__init__(**kwds)

    def compose(self) -> ComposeResult:
        yield Static(f"{self.link.source} -> {self.link.target}")
        if self.link.linked:
            yield Static("Linked", classes="hint text-success")
        elif self.link.target.exists():
            yield Static("Target is exists, will override.", classes="hint text-warning")


class Option(Container):
    cb_label = reactive("Sync")

    def __init__(self, op: _Option, **kwds):
        super().__init__(**kwds)
        self.op = op

    def compute_cb_label(self):
        return "Sync" if self.op.synced else "Unsync"

    def compose(self) -> ComposeResult:
        yield Checkbox(self.cb_label, self.op.synced, id="sync")
        with Container(id="content"):
            with Container(id="info"):
                yield Static(self.op.name, id="name", classes="text-primary")
                yield Static(self.op.description, id="description")
                yield Static(self.op.status, id="status", classes=self.op.status)
            with Container(id="depends"):
                for i in self.op.depends:
                    depends = ", ".join(self.op.depends[i])
                    yield Static(f"{i.title()} Depends: {depends}")
            with Container(id="links"):
                for link in self.op.links:
                    yield Link(link)

    @on(Checkbox.Changed, "#sync")
    def on_check_changed(self, event: Checkbox.Changed) -> None:
        self.op.synced = event.value
        event.control.label = self.cb_label


class OptionList(VerticalScroll):
    options = reactive(config.opts)

    def watch_options(self):
        self.update()

    def update(self):
        self.loading = True
        self.remove_children().__await__()
        self.mount(*[Option(op) for op in self.options]).__await__()
        self.loading = False


class Panel(Container):
    def compose(self) -> ComposeResult:
        yield Button("Sync", "success", id="sync")
        yield Button("Uninstall", "primary", id="uninstall")
        yield Button("Read config", "primary", id="read-config")

    @on(Button.Pressed, "#sync")
    def on_sync(self, event: Button.Pressed):
        getattr(self.app, "action_sync")()

    @on(Button.Pressed, "#uninstall")
    def on_uninstall(self, event: Button.Pressed):
        getattr(self.app, "uninstall")()

    @on(Button.Pressed, "#read-config")
    def on_read_config(self, event: Button.Pressed):
        getattr(self.app, "read_config")()


class MainScreen(Container):
    def compose(self) -> ComposeResult:
        yield OptionList()
        yield Panel()


class SimpleConfigSyncApp(App):
    CSS_PATH = "assets/tui.tcss"

    BINDINGS = [
        ("s", "sync", "Sync"),
        ("u", "uninstall", "Uninstall"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield MainScreen()

    def action_sync(self):
        config.sync()
        self.query_one(OptionList).update()

    def action_uninstall(self):
        config.uninstall()
        self.query_one(OptionList).update()

    def action_read_config(self):
        config.load()
        self.query_one(OptionList).update()
