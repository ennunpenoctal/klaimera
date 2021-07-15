from typing import Any, Awaitable, Callable, Optional, Tuple, Union
from pathlib import Path
import functools
import asyncio

from tomlkit import dumps, loads, items
from playsound import playsound  # type: ignore
from notify_run import Notify  # type: ignore
from aiofiles import open

from klogging import Logger

notify_run = Notify()
logger: Optional[Logger] = None


def rie(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Awaitable:
        return asyncio.get_running_loop().run_in_executor(
            None, lambda: func(*args, **kwargs)
        )

    return wrapper


async def alert() -> int:
    try:
        if (audio_path := Path(__file__).parent.joinpath("alert.wav")).exists():
            playsound(str(audio_path), block=False)

    except Exception as exc:
        if logger:
            await logger.warn("Error playing audio", exc=exc)

        return 0

    else:
        return 2


async def notify(message: str):
    @rie
    def _internal(message: str):
        notify_run.send(message)

    try:
        await _internal(message)
        return 0

    except Exception as exc:
        if logger:
            await logger.warn("Error sending push notification", exc=exc)

        return 2


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
    def int_array(
        array: Any, length: Optional[int] = None, required: bool = False
    ) -> None:
        if isinstance(array, items.Array):
            if len(array) > 0:
                check = [isinstance(item, items.Integer) for item in array]
                bool_check = [isinstance(item, bool) for item in array]
            
                if not (all(check) and not any(bool_check)):
                    if False in check:
                        fault_index = check.index(False)
                    else:
                        fault_index = bool_check.index(True)
            
                    raise ValueError(
                        f"Non-integer at index {fault_index} ({array[fault_index]})"
                    )
                
                elif length and len(array) != length:
                    raise ValueError(f"Expected int array of length {length}, got {len(array)}")

            else:
                if required:
                    raise ValueError("Values are required")


        else:
            raise TypeError("Not an array")

    @staticmethod
    def bool(item: Any) -> None:
        # NOTE: Unlike other TOMLDocument items, booleans are true booleans.
        #       https://github.com/sdispater/tomlkit/issues/119
        if not isinstance(item, bool):
            raise TypeError("Not a bool")

    @staticmethod
    def int(item: Any, range: Optional[Tuple[int, int]] = None) -> None:
        if not isinstance(item, items.Integer):
            raise TypeError("Not an integer")

        elif range and not (range[0] <= item <= range[1]):
            raise ValueError(f"Not in range of {range[0]},{range[1]} ({item})")

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
        "user.log",
        "user.log_max",
        "user.log_level",
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
        "dispatch.roll.delay",
        "dispatch.roll.wpm",
        "dispatch.claim.auto",
        "target.roll.kakera",
        "target.roll.delay",
        "target.roll.emoji",
        "target.roll.character",
        "target.roll.series",
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
        await verify("user.log", Validator.bool)
        await verify("user.log_max", Validator.int)
        await verify("user.log_level", Validator.int, range=(0, 5))

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
        await verify("dispatch.roll.delay", Validator.float_array)
        await verify("dispatch.roll.wpm", Validator.int_array, length=2, required=True)

        await verify("dispatch.claim.auto", Validator.bool)

        await verify("target.roll.kakera", Validator.int)
        await verify("target.roll.delay", Validator.float_array, length=2)
        await verify("target.roll.emoji", Validator.str)
        await verify("target.roll.character", Validator.str_array, required=True)
        await verify("target.roll.series", Validator.str_array, required=False)

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
