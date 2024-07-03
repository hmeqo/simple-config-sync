import asyncio

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
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
        elif self.op.synced and not self.link.linked and self.link.target.exists():
            yield Static("Target is exists, will be backup.", classes="status text-warning")


class ULinkList(Container):
    def __init__(self, op: SyncOp, **kwds):
        super().__init__(**kwds)
        self.op = op

    def compose(self) -> ComposeResult:
        yield Static("Links:", id="title")
        for link in self.op.links:
            yield ULink(self.op, link)


class UOption(Container):
    def __init__(self, op: SyncOp, **kwds):
        super().__init__(**kwds)
        self.op = op

    def compose(self) -> ComposeResult:
        yield Checkbox("Sync" if self.op.synced else "Unsync", self.op.synced, id="sync")
        with Container(id="content"):
            with Container(id="info"):
                yield Static(self.op.name, id="name", classes="text-primary")
                if self.op.group:
                    yield Static(f"({self.op.group})", id="group", classes="text-red")
                yield Static(self.op.description, id="description")
                yield Static(self.op.status, id="status", classes=self.op.status)
            with Container(id="depends"):
                for i in self.op.depends:
                    depends = ", ".join(self.op.depends[i])
                    yield Static(f"{i.title()} Depends: {depends}")
            yield ULinkList(self.op)

    @on(Checkbox.Changed, "#sync")
    async def on_checkbox_change(self, event: Checkbox.Changed):
        self.op.synced = event.value
        event.control.label = "Sync" if event.value else "Unsync"
        await self.query_one(ULinkList).recompose()


class UOptionList(VerticalScroll):
    def compose(self) -> ComposeResult:
        for op in config.opts:
            yield UOption(op)

    async def update(self):
        self.loading = True
        await self.recompose()
        await asyncio.sleep(0.1)
        self.loading = False

    def focus_index(self):
        checkboxes = self.query(Checkbox)
        for index, i in enumerate(checkboxes):
            if i.has_focus:
                return index

    def focus_offset(self, offset: int):
        checkboxes = self.query(Checkbox)
        index = self.focus_index()
        if index is None:
            index = 0
        else:
            index += offset
        index = max(min(index, len(checkboxes) - 1), 0)
        checkboxes[index].focus()

    def focus_down(self):
        self.focus_offset(1)

    def focus_up(self):
        self.focus_offset(-1)


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
        Binding("j", "focus_down", show=False),
        Binding("k", "focus_up", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield MainScreen()

    async def action_sync(self):
        config.sync()
        await self.query_one(UOptionList).update()

    async def action_uninstall(self):
        config.uninstall()
        await self.query_one(UOptionList).update()

    async def action_select_all(self):
        synced = all(op.synced for op in config.opts)
        for op in config.opts:
            op.synced = not synced
        await self.query_one(UOptionList).update()

    async def action_reload(self):
        config.load()
        await self.query_one(UOptionList).update()

    async def action_focus_down(self):
        self.query_one(UOptionList).focus_down()

    async def action_focus_up(self):
        self.query_one(UOptionList).focus_up()
