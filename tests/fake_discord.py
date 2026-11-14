"""Bộ giả lập discord.py TỐI THIỂU, chỉ dùng cho kiểm thử khói ngoại tuyến (không thay thế discord.py thật).

Mục đích: nạp các Cog thật, kiểm tra ràng buộc của Discord (tên/mô tả lệnh, số lựa chọn, giới hạn Embed,
số thành phần mỗi dòng...) và cho cả hành trình người chơi chạy xuyên qua mã Cog + engine + Embed.
Nó KHÔNG kiểm chứng hành vi mạng thật của Discord.
"""
from __future__ import annotations

import importlib
import inspect
import re
import sys
import types

NAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
MISSING = object()


class HTTPException(Exception):
    pass


class Embed:
    def __init__(self, title=None, description=None, color=None):
        assert title is None or len(title) <= 256, f"title quá dài ({len(title)})"
        assert description is None or len(description) <= 4096, f"description quá dài ({len(description)})"
        self.title, self.description, self.color = title, description, color
        self.fields, self.footer = [], None

    def add_field(self, *, name, value, inline=True):
        assert 0 < len(name) <= 256, f"tên field sai độ dài: {name!r}"
        assert 0 < len(value) <= 1024, f"giá trị field sai độ dài ({len(value)}): {name!r}"
        assert len(self.fields) < 25
        self.fields.append((name, value, inline))

    def set_footer(self, *, text):
        assert len(text) <= 2048
        self.footer = text

    def total(self):
        return sum(len(x or "") for x in (self.title, self.description, self.footer)) + \
            sum(len(n) + len(v) for n, v, _ in self.fields)

    def validate(self):
        assert self.total() <= 6000, f"Embed vượt 6000 ký tự ({self.total()})"
        return self


class PartialEmoji:
    def __init__(self, *, name, id=None):
        self.name, self.id = name, id


class SelectOption:
    def __init__(self, *, label, value, description=None, emoji=None):
        assert 1 <= len(label) <= 100, f"label option sai độ dài: {label!r}"
        assert 1 <= len(str(value)) <= 100
        assert description is None or 1 <= len(description) <= 100, f"description option sai: {description!r}"
        self.label, self.value, self.description, self.emoji = label, str(value), description, emoji


class _Enum:
    def __init__(self, name):
        self.name = name


class ButtonStyle:
    primary, secondary, success, danger = (_Enum(n) for n in ("primary", "secondary", "success", "danger"))


class Object:
    def __init__(self, id):
        self.id = id


class Permissions:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Intents:
    @staticmethod
    def default():
        return Intents()


# ---------------------------------------------------------------- ui
class Item:
    row = None
    callback = None
    width = 1


class Button(Item):
    def __init__(self, *, label=None, style=None, emoji=None, disabled=False, row=None):
        assert label is None or len(label) <= 80, f"label button quá dài: {label!r}"
        assert label or emoji, "button cần label hoặc emoji"
        self.label, self.style, self.emoji, self.disabled, self.row = label, style, emoji, disabled, row
        self.width = 1


class Select(Item):
    def __init__(self, *, placeholder=None, options=(), row=None, min_values=1, max_values=1):
        assert 1 <= len(options) <= 25, f"Select cần 1-25 option, có {len(options)}"
        assert placeholder is None or len(placeholder) <= 150
        self.placeholder, self.options, self.row, self.disabled = placeholder, list(options), row, False
        self.width = 5


def button(*, label=None, style=None, emoji=None, row=None, disabled=False):
    def deco(fn):
        fn.__item_kwargs__ = dict(label=label, style=style, emoji=emoji, row=row, disabled=disabled)
        return fn
    return deco


class View:
    def __init__(self, *, timeout=180.0):
        self.timeout, self.children, self.stopped = timeout, [], False
        self.message = None
        for klass in reversed(type(self).__mro__):
            for fn in klass.__dict__.values():
                kw = getattr(fn, "__item_kwargs__", None)
                if kw:
                    item = Button(**kw)
                    item.callback = (lambda f, it: (lambda itx: f(self, itx, it)))(fn, item)
                    self.add_item(item)

    def add_item(self, item):
        assert len(self.children) < 25, "View quá 25 thành phần"
        if item.row is None:
            for r in range(5):
                if sum(c.width for c in self.children if c.row == r) + item.width <= 5:
                    item.row = r
                    break
        assert item.row is not None and item.row < 5, "hết chỗ trên 5 dòng"
        assert sum(c.width for c in self.children if c.row == item.row) + item.width <= 5, \
            f"dòng {item.row} vượt 5 đơn vị"
        self.children.append(item)

    def stop(self):
        self.stopped = True

    async def interaction_check(self, interaction):
        return True

    async def on_timeout(self):
        pass


ui = types.SimpleNamespace(View=View, Select=Select, Button=Button, button=button, Item=Item)


# ---------------------------------------------------------------- app_commands
class AppCommandError(Exception):
    pass


class CheckFailure(AppCommandError):
    pass


class Choice:
    def __init__(self, *, name, value):
        assert 1 <= len(name) <= 100, f"Choice name sai: {name!r}"
        assert not isinstance(value, str) or 1 <= len(value) <= 100
        self.name, self.value = name, value

    def __class_getitem__(cls, _):
        return cls


class Range:
    def __class_getitem__(cls, _):
        return cls


def _params(fn):
    ps = list(inspect.signature(fn).parameters.values())
    return ps[2:]  # bỏ self, interaction


class Command:
    def __init__(self, callback, name, description):
        assert NAME_RE.match(name), f"tên lệnh không hợp lệ: {name!r}"
        assert 1 <= len(description) <= 100, f"mô tả lệnh {name!r} sai độ dài ({len(description)})"
        self.callback, self.name, self.description = callback, name, description
        self.checks = list(getattr(callback, "__checks__", []))
        ps = _params(callback)
        names = [p.name for p in ps]
        for n in names:
            assert NAME_RE.match(n), f"tham số {n!r} của {name!r} phải là chữ thường"
        seen_optional = False
        for p in ps:
            if p.default is not inspect.Parameter.empty:
                seen_optional = True
            else:
                assert not seen_optional, f"{name}: tham số bắt buộc {p.name!r} đứng sau tham số tùy chọn"
        assert len(ps) <= 25
        for key, choices in getattr(callback, "__choices__", {}).items():
            assert key in names, f"{name}: choices cho tham số không tồn tại {key!r}"
            assert 1 <= len(choices) <= 25, f"{name}.{key}: {len(choices)} choices"
        for key, text in getattr(callback, "__describe__", {}).items():
            assert key in names, f"{name}: describe cho tham số không tồn tại {key!r}"
            assert 1 <= len(text) <= 100, f"{name}.{key}: mô tả tham số dài {len(text)}"
        self.params = names
        self.parent = None

    @property
    def qualified_name(self):
        return self.name


class Group:
    def __init__(self, *, name, description, **kw):
        assert NAME_RE.match(name)
        assert 1 <= len(description) <= 100, f"mô tả nhóm {name!r} sai độ dài"
        self.name, self.description, self.commands = name, description, []

    def command(self, *, name=None, description="..."):
        def deco(fn):
            cmd = Command(fn, name or fn.__name__, description)
            assert all(c.name != cmd.name for c in self.commands), f"trùng lệnh {self.name}/{cmd.name}"
            assert len(self.commands) < 25, "nhóm quá 25 lệnh con"
            cmd.parent = self
            self.commands.append(cmd)
            return cmd
        return deco


def command(*, name=None, description="..."):
    def deco(fn):
        return Command(fn, name or fn.__name__, description)
    return deco


def check(predicate):
    def deco(fn):
        target = fn.callback if isinstance(fn, Command) else fn
        target.__checks__ = getattr(target, "__checks__", []) + [predicate]
        if isinstance(fn, Command):
            fn.checks.append(predicate)
        return fn
    return deco


def choices(**kw):
    def deco(fn):
        target = fn.callback if isinstance(fn, Command) else fn
        target.__choices__ = {**getattr(target, "__choices__", {}), **kw}
        if isinstance(fn, Command):
            Command.__init__(fn, fn.callback, fn.name, fn.description)
        return fn
    return deco


def describe(**kw):
    def deco(fn):
        target = fn.callback if isinstance(fn, Command) else fn
        target.__describe__ = {**getattr(target, "__describe__", {}), **kw}
        if isinstance(fn, Command):
            Command.__init__(fn, fn.callback, fn.name, fn.description)
        return fn
    return deco


class CommandTree:
    def __init__(self):
        self.items, self.on_error = [], None

    def add(self, item):
        assert all(i.name != item.name for i in self.items), f"trùng lệnh gốc {item.name}"
        self.items.append(item)
        assert len(self.items) <= 100, "quá 100 lệnh gốc"

    def get_commands(self):
        return list(self.items)

    def copy_global_to(self, *, guild):
        pass

    async def sync(self, **kw):
        return []


app_commands = types.SimpleNamespace(
    command=command, Group=Group, check=check, choices=choices, describe=describe, Choice=Choice, Range=Range,
    CheckFailure=CheckFailure, AppCommandError=AppCommandError, Command=Command, CommandTree=CommandTree)


# ---------------------------------------------------------------- ext.commands / tasks
class Cog:
    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        cls.__app_items__ = [v for v in cls.__dict__.values()
                             if isinstance(v, (Command, Group)) and getattr(v, "parent", None) is None]

    async def cog_load(self):
        pass

    async def cog_unload(self):
        pass


class Loop:
    def __init__(self, fn, seconds=0, hours=0):
        self.fn, self.interval, self.started = fn, (seconds, hours), False
        self._before = None
        self.owner = None

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        bound = Loop(self.fn, *self.interval)
        bound.owner, bound._before = obj, self._before
        return bound

    def before_loop(self, fn):
        self._before = fn
        return fn

    def change_interval(self, *, seconds=0, hours=0):
        assert seconds > 0 or hours > 0
        self.interval = (seconds, hours)

    def start(self):
        self.started = True

    def cancel(self):
        self.started = False

    async def __call__(self, *a):
        return await self.fn(self.owner, *a)


def loop(*, seconds=0, hours=0):
    def deco(fn):
        return Loop(fn, seconds, hours)
    return deco


class Bot:
    def __init__(self, command_prefix=None, intents=None, help_command=None):
        self.tree = CommandTree()
        self.cogs, self.user, self._channels = {}, "TBPT#0001", {}
        self.app_emojis: dict[str, int] = {}

    def run(self, *a, **k):  # pragma: no cover
        raise RuntimeError("stub")

    async def add_cog(self, cog):
        self.cogs[type(cog).__name__] = cog
        for item in type(cog).__app_items__:
            self.tree.add(item)
        await cog.cog_load()

    def get_cog(self, name):
        return self.cogs.get(name)

    async def load_extension(self, name):
        await importlib.import_module(name).setup(self)

    async def wait_until_ready(self):
        pass

    def get_channel(self, cid):
        return self._channels.get(cid)

    async def close(self):
        pass

    # API emoji ứng dụng giả
    async def fetch_application_emojis(self):
        return [types.SimpleNamespace(name=n, id=i) for n, i in self.app_emojis.items()]

    async def create_application_emoji(self, *, name, image):
        assert re.fullmatch(r"[A-Za-z0-9_]{2,32}", name), f"tên emoji sai: {name}"
        assert image[:8] == b"\x89PNG\r\n\x1a\n" and len(image) <= 256 * 1024, "ảnh emoji không hợp lệ"
        eid = 1_204_000_000_000_000_000 + len(self.app_emojis)  # ID thật dài 19 chữ số
        self.app_emojis[name] = eid
        return types.SimpleNamespace(name=name, id=eid)


def install():
    """Đăng ký module giả vào sys.modules (không làm gì nếu discord.py thật đã có)."""
    if "discord" in sys.modules and not getattr(sys.modules["discord"], "__fake__", False):
        return False
    d = types.ModuleType("discord")
    d.__fake__ = True
    for k, v in dict(Embed=Embed, PartialEmoji=PartialEmoji, SelectOption=SelectOption, ButtonStyle=ButtonStyle,
                     Object=Object, Permissions=Permissions, Intents=Intents, HTTPException=HTTPException, ui=ui,
                     app_commands=app_commands, Interaction=object, User=object, Member=object, TextChannel=object,
                     Message=object, utils=types.SimpleNamespace(MISSING=MISSING)).items():
        setattr(d, k, v)
    ext = types.ModuleType("discord.ext")
    commands = types.ModuleType("discord.ext.commands")
    commands.Cog, commands.Bot, commands.when_mentioned = Cog, Bot, object()
    tasks = types.ModuleType("discord.ext.tasks")
    tasks.loop = loop
    ext.commands, ext.tasks = commands, tasks
    d.ext = ext
    sys.modules.update({"discord": d, "discord.ext": ext, "discord.ext.commands": commands,
                        "discord.ext.tasks": tasks, "discord.ui": types.ModuleType("discord.ui"),
                        "discord.app_commands": types.ModuleType("discord.app_commands")})
    sys.modules["discord.ui"].__dict__.update(ui.__dict__)
    sys.modules["discord.app_commands"].__dict__.update(app_commands.__dict__)
    return True
