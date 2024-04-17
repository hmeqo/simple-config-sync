from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import var
from textual.widgets import Button, Checkbox, Footer, Header, Static

from .config import Link, SyncOp, config


class ULink(Horizontal):
    def __init__(self, op: SyncOp, link: Link, **kwds):
        super().__init__(**kwds)
        self.op = op
        self.link = link

    def compose(self) -> ComposeResult:
        yield Static(f"{self.link.source} -> {self.link.target}")
        if (self.op.synced or self.op.lock_op.synced) and self.link.linked:
            yield Static("Linked", classes="hint text-success")
        elif self.op.synced and self.link.target.exists():
            yield Static("Target is exists, will override.", classes="status text-warning")


class UOption(Container):
    def __init__(self, op: SyncOp, **kwds):
        super().__init__(**kwds)
        self.op = op

    def compose(self) -> ComposeResult:
        yield Checkbox("Sync", self.op.synced, id="sync")
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
                yield Static("Links:", id="title")
                for link in self.op.links:
                    yield ULink(self.op, link)

    @on(Checkbox.Changed, "#sync")
    def on_check_changed(self, event: Checkbox.Changed) -> None:
        self.op.synced = event.value
        event.control.label = "Sync" if event.value else "Unsync"
        container = self.query_one("#links", Container)
        container.remove_children(ULink).__await__()
        container.mount(*[ULink(self.op, link) for link in self.op.links]).__await__()


class UOptionList(VerticalScroll):
    options = var(config.opts)

    def watch_options(self):
        self.update()

    def update(self):
        self.loading = True
        self.remove_children().__await__()
        self.mount(*[UOption(op) for op in self.options]).__await__()
        self.loading = False


class Panel(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Button("Sync", "success", id="sync")
        yield Button("Uninstall", "primary", id="uninstall")
        yield Button("Select All", "primary", id="select-all")
        yield Button("Reload", "primary", id="reload")

    @on(Button.Pressed)
    async def on_btn_press(self, event: Button.Pressed):
        await self.app.run_action(str(event.button.id).replace("-", "_"))


class MainScreen(Container):
    def compose(self) -> ComposeResult:
        yield UOptionList()
        yield Panel()


class SimpleConfigSyncApp(App):
    CSS_PATH = "assets/tui.tcss"

    BINDINGS = [
        ("s", "sync", "Sync"),
        ("u", "uninstall", "Uninstall"),
        ("a", "select_all", "Select All"),
        ("r", "reload", "Reload"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield MainScreen()

    def action_sync(self):
        config.sync()
        self.query_one(UOptionList).update()

    def action_uninstall(self):
        config.uninstall()
        self.query_one(UOptionList).update()

    def action_select_all(self):
        synced = all(op.synced for op in config.opts)
        for op in config.opts:
            op.synced = not synced
        self.query_one(UOptionList).update()

    def action_reload(self):
        config.load()
        self.query_one(UOptionList).update()
