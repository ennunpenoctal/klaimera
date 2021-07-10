import functools
import asyncio

from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Union
from tomlkit import dumps, loads, items
from aiofiles import open


def rie(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Awaitable:
        return asyncio.get_running_loop().run_in_executor(
            None, lambda: func(*args, **kwargs)
        )

    return wrapper


def task(coro: Awaitable) -> asyncio.Task:
    loop = asyncio.get_event_loop()
    return loop.create_task(coro)


class Validator:
    @staticmethod
    def str_array(array: Any, required: bool = False) -> None:
        if isinstance(array, items.Array):
            check = [isinstance(item, items.String) for item in array]
            if not (all(check) or (len(array) == 0 and required)):
                if not all(check):
                    fault_index = check.index(False)
                    raise ValueError(
                        f"Non-string at index {fault_index} ({array[fault_index]})"
                    )

                else:
                    raise ValueError("Is required to have at least one value")

        else:
            raise TypeError("Not an array")

    @staticmethod
    def float_array(array: Any, length: Optional[int] = None) -> None:
        if isinstance(array, items.Array):
            check = [isinstance(item, items.Float) for item in array]
            if not (all(check) and ((length and length == len(array)) or not length)):
                if not all(check):
                    fault_index = check.index(False)
                    raise ValueError(
                        f"Non-float at index {fault_index} ({array[fault_index]})"
                    )

                else:
                    raise ValueError(f"Is length {len(array)}, minimum {length}")

        else:
            raise TypeError("Not an array")

    @staticmethod
    def int_array(array: Any) -> None:
        if isinstance(array, items.Array):
            check = [isinstance(item, items.Integer) for item in array]
            bool_check = [isinstance(item, bool) for item in array]

            if not (all(check) and not all(bool_check)):
                fault_index = check.index(False)
                raise ValueError(
                    f"Non-integer at index {fault_index} ({array[fault_index]})"
                )

        else:
            raise TypeError("Not an array")

    @staticmethod
    def bool(item: Any) -> None:
        # NOTE: Unlike other TOMLDocument items, booleans are true booleans.
        #       https://github.com/sdispater/tomlkit/issues/119
        if not isinstance(item, bool):
            raise TypeError("Not a bool")

    @staticmethod
    def int(item: Any) -> None:
        if not isinstance(item, items.Integer):
            raise TypeError("Not an integer")

    @staticmethod
    def str(item: Any) -> None:
        if not isinstance(item, items.String):
            raise TypeError("Not a string")


class Config:
    String = items.String
    Integer = items.Integer
    Float = items.Float
    Boolean = items.Bool
    Array = items.Array

    real_types = Union[str, int, float, bool]
    toml_types = Union[items.String, items.Integer, items.Float, items.Bool]

    ids = (
        "user.token",
        "user.notify",
        "user.sound",
        "commands.enable",
        "commands.status",
        "commands.statusPublic",
        "commands.config",
        "commands.dispatch",
        "commands.notify",
        "commands.emoji",
        "commands.emojiSuccess",
        "commands.emojiFailure",
        "commands.emojiInvalid",
        "commands.warn",
        "commands.warnMessage",
        "dispatch.roll.auto",
        "dispatch.roll.command",
        "dispatch.claim.auto",
        "dispatch.claim.delay",
        "dispatch.claim.emoji",
        "target.roll.character",
        "target.roll.series",
        "target.roll.kakera",
        "target.claim.series",
        "server.id",
        "server.channel",
        "server.settings.claim",
        "server.settings.claimReset",
        "server.settings.claimExpire",
        "server.settings.claimAnchor",
        "server.settings.rolls",
    )

    type_map = {
        str: String,
        int: Integer,
        float: Float,
        bool: Boolean,
        list: Array,
    }

    def __init__(self) -> None:
        self.path = Path(__file__).parent.joinpath("config.toml").absolute()

    async def init(self) -> None:
        self.file = await open(self.path, "r+")
        self.file_mtime = int(self.path.stat().st_mtime)
        self.toml = loads(await self.file.read())

    async def get(self, id: str) -> toml_types:
        if id in self.ids:
            joiner = "']['"
            return eval(f"self.toml['{joiner.join(id.split('.'))}']")
        else:
            raise KeyError("Is a non-existent key")

    async def set(self, id: str, value: real_types):
        if id in self.ids:
            joiner = "']['"
            exec(f"self.toml[{']['.join(id.split('.'))}] = value")
        else:
            raise KeyError("Is a non-existent key")

    async def load(self):
        # NOTE: If you see a clusterfuck of Pyright error messages, relax.
        #       https://github.com/sdispater/tomlkit/issues/111

        await self.file.seek(0)
        self.toml = loads(await self.file.read())

        async def verify(id: str, validator: Callable, **kwargs):
            try:
                validator(await self.get(id), **kwargs)

            except Exception as err:
                raise err.__class__(id + f" <- {err}")

        await verify("user.token", Validator.str)
        await verify("user.notify", Validator.bool)
        await verify("user.sound", Validator.bool)

        await verify("commands.enable", Validator.bool)
        await verify("commands.status", Validator.bool)
        await verify("commands.statusPublic", Validator.bool)
        await verify("commands.config", Validator.bool)
        await verify("commands.dispatch", Validator.bool)
        await verify("commands.notify", Validator.bool)
        await verify("commands.emoji", Validator.bool)
        await verify("commands.emojiSuccess", Validator.str)
        await verify("commands.emojiFailure", Validator.str)
        await verify("commands.emojiInvalid", Validator.str)
        await verify("commands.emoji", Validator.bool)
        await verify("commands.warn", Validator.bool)
        await verify(
            "commands.warnMessage",
            Validator.str_array,
            required=True if await self.get("commands.warn") else False,
        )

        await verify("dispatch.roll.auto", Validator.bool)
        await verify("dispatch.roll.command", Validator.str)

        await verify("dispatch.claim.auto", Validator.bool)
        await verify("dispatch.claim.delay", Validator.float_array, length=2)
        await verify("dispatch.claim.emoji", Validator.str)

        await verify("target.roll.character", Validator.str_array, required=True)
        await verify("target.roll.series", Validator.str_array, required=False)
        await verify("target.roll.kakera", Validator.int)

        await verify("target.claim.series", Validator.str_array, required=False)

        await verify("server.id", Validator.int)
        await verify("server.channel", Validator.int_array)

        await verify("server.settings.claim", Validator.int)
        await verify("server.settings.claimReset", Validator.int)
        await verify("server.settings.claimExpire", Validator.int)
        await verify("server.settings.claimAnchor", Validator.int)
        await verify("server.settings.rolls", Validator.int)

    async def dump(self):
        await self.file.seek(0)
        await self.file.write(dumps(self.toml))
        await self.file.truncate()

    @rie
    def last_modified(self) -> int:
        if self.path.exists():
            return int(self.path.stat().st_mtime)

        else:
            return 0
