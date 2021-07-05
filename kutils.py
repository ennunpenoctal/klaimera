import functools
import asyncio

from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Union, NamedTuple
from tomlkit import dumps, loads, items
from tomlkit.toml_document import TOMLDocument
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


class Config:
    String = items.String
    Integer = items.Integer
    Boolean = items.Bool
    List = items.List

    def __init__(self) -> None:
        self.path = Path(__file__).parent.joinpath("config.toml").absolute()

    async def load(self):
        if not hasattr(self, "file"):
            if not self.path.exists():
                print(f"{self.path} does not exist")

            self.file = await open(self.path, "r+")
            self.mtime = int(self.path.stat().st_mtime)
            self.toml = loads(await self.file.read())

        await self.file.seek(0)

        self.user_token = self.toml["user"]["token"]
        self.user_notify = self.toml["user"]["notify"]
        self.user_sound = self.toml["user"]["sound"]

        self.commands_enable = self.toml["commands"]["enable"]
        self.commands_status = self.toml["commands"]["status"]
        self.commands_config = self.toml["commands"]["config"]
        self.commands_dispatch = self.toml["commands"]["dispatch"]
        self.commands_notify = self.toml["commands"]["notify"]
        self.commands_log = self.toml["commands"]["log"]
        self.commands_emoji = self.toml["commands"]["emoji"]
        self.commands_emojiSuccess = self.toml["commands"]["emojiSuccess"]
        self.commands_emojiFailure = self.toml["commands"]["emojiFailure"]
        self.commands_emojiInvalid = self.toml["commands"]["emojiInvalid"]
        self.commands_warnMessage = self.toml["commands"]["warnMessage"]

        self.dispatch_roll_auto = self.toml["dispatch"]["roll"]["auto"]
        self.dispatch_roll_command = self.toml["dispatch"]["roll"]["command"]

        self.dispatch_claim_auto = self.toml["dispatch"]["claim"]["auto"]
        self.dispatch_claim_threshold = self.toml["dispatch"]["claim"]["threshold"]
        self.dispatch_claim_delay = self.toml["dispatch"]["claim"]["delay"]
        self.dispatch_claim_emoji = self.toml["dispatch"]["claim"]["emoji"]

        self.target_character = self.toml["target"]["character"]
        self.target_series = self.toml["target"]["series"]

        self.server_channel = self.toml["server"]["channel"]

        self.server_settings_claim = self.toml["server"]["settings"]["claim"]
        self.server_settings_claimReset = self.toml["server"]["settings"]["claimReset"]
        self.server_settings_claimExpire = self.toml["server"]["settings"][
            "claimExpire"
        ]
        self.server_settings_claimAnchor = self.toml["server"]["settings"][
            "claimAnchor"
        ]
        self.server_settings_rolls = self.toml["server"]["settings"]["rolls"]

        if not hasattr(self, "idmap"):  # Prevent idmap recreation during reloads
            self.idmap = {
                "user.token": self.user_token,
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
                "dispatch.roll.auto": self.dispatch_roll_auto,
                "dispatch.roll.command": self.dispatch_roll_command,
                "dispatch.claim.auto": self.dispatch_claim_auto,
                "dispatch.claim.threshold": self.dispatch_claim_threshold,
                "dispatch.claim.delay": self.dispatch_claim_delay,
                "dispatch.claim.emoji": self.dispatch_claim_emoji,
                "target.character": self.target_character,
                "target.series": self.target_series,
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
