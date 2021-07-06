import functools
import asyncio

from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Union, NamedTuple
from tomlkit import dumps, loads, items
from tomlkit.toml_document import TOMLDocument
from aiofiles import open

# TODO: Fix config validation issues


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


class Config:
    String = items.String
    Integer = items.Integer
    Boolean = items.Bool
    List = items.List

    def __init__(self) -> None:
        self.path = Path(__file__).parent.joinpath("config.toml").absolute()

    @staticmethod
    def _verify_bool(item: Any) -> bool:
        # NOTE: Unlike other TOMLDocument items, booleans are true booleans.
        #       https://github.com/sdispater/tomlkit/issues/119
        if isinstance(item, bool):
            return item

        else:
            raise TypeError(
                "Invalid configuration type. See Traceback for more details."
            )

    @staticmethod
    def _verify_float(item: Any) -> items.Float:
        if isinstance(item, items.Float):
            return item

        else:
            raise TypeError(
                "Invalid configuration type. See Traceback for more details."
            )

    @staticmethod
    def _verify_int(item: Any) -> items.Integer:
        if isinstance(item, items.Integer):
            return item

        else:
            raise TypeError(
                "Invalid configuration type. See Traceback for more details."
            )

    @staticmethod
    def _verify_str(item: Any) -> items.String:
        if isinstance(item, items.String):
            return item

        else:
            raise TypeError(
                "Invalid configuration type. See Traceback for more details."
            )

    @staticmethod
    def _verify_str_array(array: Any, required: bool = False) -> items.Array:
        if isinstance(array, items.Array):
            check = [isinstance(item, items.String) for item in array]
            if all(check) or (len(array) == 0 and required):
                return array

            else:
                raise TypeError(
                    "Invalid array due to type mismatch or empty array. "
                    " See traceback for more details."
                )

        else:
            raise TypeError(
                "Invalid configuration type. See traceback for more details."
            )

    @staticmethod
    def _verify_int_array(array: Any, length: Optional[int] = None) -> items.Array:
        if isinstance(array, items.Array):
            check = [isinstance(item, items.Integer) for item in array]
            # NOTE: This is required as isinstance(True, int) == True because
            #       historical reasons
            bool_check = [isinstance(item, bool) for item in array]
            if (all(check) and not all(bool_check)) and (
                (length and length == len(array)) or not length
            ):
                return array

            else:
                raise TypeError(
                    "Invalid type in array. See traceback for more details."
                )

        else:
            raise TypeError(
                "Invalid configuration type. See traceback for more details."
            )

    async def load(self):
        if not hasattr(self, "file"):
            if not self.path.exists():
                print(f"{self.path} does not exist")

            self.file = await open(self.path, "r+")
            self.mtime = int(self.path.stat().st_mtime)
            self.toml = loads(await self.file.read())

        else:
            await self.file.seek(0)
            self.toml = loads(await self.file.read())

        # NOTE: If you see a clusterfuck of Pyright error messages, relax.
        #       https://github.com/sdispater/tomlkit/issues/111

        self.user_token = self._verify_str(self.toml["user"]["token"])
        self.user_notify = self._verify_bool(self.toml["user"]["notify"])
        self.user_sound = self._verify_bool(self.toml["user"]["sound"])

        self.commands_enable = self._verify_bool(self.toml["commands"]["enable"])
        self.commands_status = self._verify_bool(self.toml["commands"]["status"])
        self.commands_config = self._verify_bool(self.toml["commands"]["config"])
        self.commands_dispatch = self._verify_bool(self.toml["commands"]["dispatch"])
        self.commands_notify = self._verify_bool(self.toml["commands"]["notify"])
        self.commands_log = self._verify_bool(self.toml["commands"]["log"])
        self.commands_emoji = self._verify_bool(self.toml["commands"]["emoji"])
        self.commands_emojiSuccess = self._verify_str(
            self.toml["commands"]["emojiSuccess"]
        )
        self.commands_emojiFailure = self._verify_str(
            self.toml["commands"]["emojiFailure"]
        )
        self.commands_emojiInvalid = self._verify_str(
            self.toml["commands"]["emojiInvalid"]
        )
        self.commands_warn = self._verify_bool(self.toml["commands"]["warn"])
        self.commands_warnMessage = self._verify_str_array(
            self.toml["commands"]["warnMessage"],
            required=True if self.commands_warn else False,
        )

        self.dispatch_roll_auto = self._verify_bool(
            self.toml["dispatch"]["roll"]["auto"]
        )
        self.dispatch_roll_command = self._verify_str(
            self.toml["dispatch"]["roll"]["command"]
        )

        self.dispatch_claim_auto = self._verify_bool(
            self.toml["dispatch"]["claim"]["auto"]
        )
        self.dispatch_claim_threshold = self._verify_int(
            self.toml["dispatch"]["claim"]["threshold"]
        )
        self.dispatch_claim_delay = self._verify_int_array(
            self.toml["dispatch"]["claim"]["delay"], length=2
        )
        self.dispatch_claim_emoji = self._verify_str(
            self.toml["dispatch"]["claim"]["emoji"]
        )

        self.target_character = self._verify_str_array(
            self.toml["target"]["character"], required=True
        )
        self.target_series = self._verify_str_array(
            self.toml["target"]["series"], required=True
        )

        self.server_channel = self._verify_int(self.toml["server"]["channel"])

        self.server_settings_claim = self._verify_int(
            self.toml["server"]["settings"]["claim"]
        )
        self.server_settings_claimReset = self._verify_int(
            self.toml["server"]["settings"]["claimReset"]
        )
        self.server_settings_claimExpire = self._verify_int(
            self.toml["server"]["settings"]["claimExpire"]
        )
        self.server_settings_claimAnchor = self._verify_int(
            self.toml["server"]["settings"]["claimAnchor"]
        )
        self.server_settings_rolls = self.toml["server"]["settings"]["rolls"]

        if not hasattr(self, "idmap"):  # Prevent idmap recreation during reloads
            self.idmap = {
                "user.notify": self.user_notify,
                "user.sound": self.user_sound,
                "commands.enable": self.commands_enable,
                "commands.status": self.commands_status,
                "commands.config": self.commands_config,
                "commands.dispatch": self.commands_dispatch,
                "commands.notify": self.commands_notify,
                "commands.log": self.commands_log,
                "commands.emoji": self.commands_emoji,
                "commands.emojiSuccess": self.commands_emojiSuccess,
                "commands.emojiFailure": self.commands_emojiFailure,
                "commands.emojiInvalid": self.commands_emojiInvalid,
                "commands.warnMessage": self.commands_warnMessage,
                "dispatch.roll.auto": self.dispatch_roll_auto,
                "dispatch.roll.command": self.dispatch_roll_command,
                "dispatch.claim.auto": self.dispatch_claim_auto,
                "dispatch.claim.threshold": self.dispatch_claim_threshold,
                "dispatch.claim.delay": self.dispatch_claim_delay,
                "dispatch.claim.emoji": self.dispatch_claim_emoji,
                "target.character": self.target_character,
                "target.series": self.target_series,
                "server.channel": self.server_channel,
                "server.settings.claim": self.server_settings_claim,
                "server.settings.claimReset": self.server_settings_claimReset,
                "server.settings.claimExpire": self.server_settings_claimExpire,
                "server.settings.claimAnchor": self.server_settings_claimAnchor,
                "server.settings.rolls": self.server_settings_rolls,
            }

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
