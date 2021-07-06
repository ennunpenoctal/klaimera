from typing import Callable, NamedTuple, Awaitable, List, Union
from datetime import datetime, timedelta
from statistics import median
from random import uniform
from bisect import insort
from enum import Enum
from time import time

from asyncio import run, sleep, get_event_loop
from watchgod import awatch
from uvloop import install
import discord

import klogging
import kutils

MUDAE_AID = 432610292342587392
KLAIMERA_START = time()
logger = klogging


class EventType(Enum):
    RELOAD = 0
    ROLL = 1
    RESET_CLAIM = 2
    RESET_KAKERA = 3
    RESET_DAILY = 4
    TIME_SYNC = 5
    EVENTMGR_BENCH = 6


class Event(NamedTuple):
    type: Union[EventType, str]
    timestamp: int
    call: Callable
    recur: bool = False
    delta: timedelta = timedelta()

    def __lt__(self, other_event):
        return self.timestamp < other_event.timestamp


class EventManager:
    def __init__(self) -> None:
        self.events: List[Event] = []
        self.overhead: Union[float, int] = 0

    async def dispatcher(self, interval: int = 1, bench: bool = False) -> None:
        while True:
            ctime = int(time())

            if len(self.events) > 0 and (
                ctime == self.events[0].timestamp or ctime > self.events[0].timestamp
            ):
                event: Event = self.events.pop(0)

                if bench is False:
                    if event.recur:
                        next_timestamp = int(
                            (
                                datetime.fromtimestamp(event.timestamp) + event.delta
                            ).timestamp()
                        )

                        insort(
                            self.events,
                            Event(
                                type=event.type,
                                timestamp=next_timestamp,
                                call=event.call,
                                recur=event.recur,
                                delta=event.delta,
                            ),
                        )

                        add_info = (
                            f"recurring dispatch. ({event.delta})"
                            f"Next call scheduled for {next_timestamp}."
                        )

                    else:
                        add_info = "dispatch."

                    await logger.info(f"Callling scheduled {add_info}")

                loop = get_event_loop()
                loop.create_task(event.call())

            if bench:
                break

            await sleep(interval - self.overhead)

    async def benchmark(self):
        async def empty():
            pass

        times = []

        for _ in range(10):
            self.events.insert(
                0,
                Event(type="benchmark", timestamp=int(time()), call=empty, recur=False),
            )

            stime = time()
            await self.dispatcher(bench=True)
            times.append(time() - stime)

        self.overhead = median(times)
        await logger.debug(f"Dispatch benchmarked at {self.overhead}s")

    async def dispatch(
        self,
        type: Union[EventType, str],
        call: Callable,
        at: Union[timedelta, int, datetime],
        recur: bool = False,
        delta: timedelta = timedelta(),
    ) -> None:
        if isinstance(at, timedelta):
            timestamp = int(time() + at.total_seconds())
            time_info = datetime.now() + at
        elif isinstance(at, datetime):
            timestamp = int(at.timestamp())
            time_info = at
        else:
            timestamp = at
            time_info = datetime.fromtimestamp(at)

        if recur:
            recur_info = f", recurring every {delta}."
        else:
            recur_info = "."

        logger.info(f"Dispatched {type} for {time_info}{recur_info}")

        self.events.append(
            Event(
                type=type,
                timestamp=timestamp,
                call=call,
                recur=recur,
                delta=delta,
            )
        )


class Klaimera(discord.Client):
    async def command_dispatch(self) -> int:
        return 0

    async def command_exec(self, message: discord.Message) -> int:
        # Return Codes:
        # -1 : OK, Do not react with emojiSuccess
        #  0 : OK
        #  1 : Invalid
        #  2 : Error

        if len(scmd := message.content.lstrip("kmra ").split(" ", 1)) == 1:
            base, args = scmd[0], None
        else:
            base, args = scmd

        if base == "config":
            # kmra config targets.character add "Yuki Nagato"
            #      <base> <0--------------- 1-- 2------------
            if args and len(sarg := args.split(" ")) >= 1:
                if len(sarg) == 1:
                    if sarg[0] == "reload":
                        try:
                            await self.config.load()
                        except Exception as err:
                            await logger.warn("Error reloading configuration", err=err)
                            return 2
                        else:
                            await logger.info("Reloaded configuration")
                            return 0

                    elif sarg[0] in self.config.idmap:
                        await message.reply(f"```\n{self.config.idmap[sarg[0]]}\n```")
                        return -1

                    else:
                        return 1

                elif len(sarg) == 3 and sarg[0] in self.config.idmap:
                    # TODO: Configuration write commands
                    if sarg[1] == "set":
                        ...
                        return 0

                    elif sarg[1] == "add":
                        ...
                        return 0

                    elif sarg[1] == "rem":
                        ...
                        return 0

                    else:
                        return 1

                else:
                    return 1

            elif not args:
                warn_message_str = "\n".join(
                    [f"    {mesg}," for mesg in self.config.commands_warnMessage]
                )
                target_character_str = "\n".join(
                    [f"    {mesg}," for mesg in self.config.target_character]
                )
                target_series_str = "\n".join(
                    [f"    {mesg}," for mesg in self.config.target_series]
                )

                await message.reply(
                    (
                        "```"
                        "\n[user]\n"
                        f"notify = {self.config.user_notify}\n"
                        f"sound  = {self.config.user_sound}\n"
                        "\n[commands]\n"
                        f"enable       = {self.config.commands_enable}\n"
                        f"status       = {self.config.commands_status}\n"
                        f"config       = {self.config.commands_config}\n"
                        f"dispatch     = {self.config.commands_dispatch}\n"
                        f"notify       = {self.config.commands_notify}\n"
                        f"emoji        = {self.config.commands_emoji}\n"
                        f"emojiSuccess = {self.config.commands_emojiSuccess}\n"
                        f"emojiFailure = {self.config.commands_emojiFailure}\n"
                        f"emojiInvalid = {self.config.commands_emojiInvalid}\n"
                        "warnMessage  = [\n"
                        f"{warn_message_str}"
                        "\n]\n"
                        "\n[dispatch.roll]\n"
                        f"auto    = {self.config.dispatch_roll_auto}\n"
                        f"command = {self.config.dispatch_roll_command}\n"
                        "\n[dispatch.claim]\n"
                        f"auto      = {self.config.dispatch_claim_auto}\n"
                        f"threshold = {self.config.dispatch_claim_threshold}\n"
                        f"delay     = {self.config.dispatch_claim_delay}\n"
                        f"emoji     = {self.config.dispatch_claim_emoji}"
                        "\n[target]\n"
                        f"character = [\n"
                        f"{target_character_str}"
                        "\n]\n"
                        f"series    = [\n"
                        f"{target_series_str}"
                        "\n]\n"
                        "\n[server]\n"
                        f"channel = {self.config.server_channel}\n"
                        "\n[server.settings]\n"
                        f"claim       = {self.config.server_settings_claim}\n"
                        f"claimExpire = {self.config.server_settings_claimExpire}\n"
                        f"claimReset  = {self.config.server_settings_claimReset}\n"
                        f"claimAnchor = {self.config.server_settings_claimAnchor}\n"
                        f"rolls       = {self.config.server_settings_rolls}\n"
                        "```"
                    )
                )
                return -1

            else:
                return 1

        elif base == "dispatch":
            # kmra dispatch roll 0
            if args is None:
                await message.reply(str(self.eventmgr.events))

            elif len(sarg := args.split(" ")) == 2:
                ...
                return 0

            else:
                return 1

        elif base == "notify":
            if args == "push":
                ...
                return 0

            elif args == "sound":
                ...
                return 0

            else:
                return 1

        elif base == "status" and self.config.commands_statusPublic:
            kmra_start_dt = datetime.fromtimestamp(KLAIMERA_START)
            uptime = datetime.now() - kmra_start_dt

            await message.reply(
                f"klaimera is running, and has been for `{uptime}`."
                f" (since `{kmra_start_dt}`)"
            )

            return -1

        else:
            return 1

        return 0

    async def bootstrap(self):
        self.eventmgr = EventManager()

        await self.eventmgr.benchmark()

        loop = get_event_loop()
        loop.create_task(self.eventmgr.dispatcher())

        self.config = kutils.Config()
        await self.config.load()

        async def reloader():
            if self.config.mtime != self.config.last_modified():
                try:
                    await self.config.load()

                except Exception as exc:
                    await logger.warn("Unsuccessful config reload", exc=exc)

        await self.eventmgr.dispatch(
            type=EventType.RELOAD,
            call=reloader,
            at=timedelta(hours=1),
            recur=True,
            delta=timedelta(minutes=30),
        )

    async def on_ready(self):
        await logger.info(f"Ready as {self.user}.")

    async def on_message(self, message: discord.Message):
        if (
            message.author.id == self.user.id
            and message.content.startswith("kmra ")
            or message.content.startswith("kmra status")
        ):
            if (retcode := await self.command_exec(message)) == 0:
                await message.add_reaction(str(self.config.commands_emojiSuccess))
            elif retcode == 1:
                await message.add_reaction(str(self.config.commands_emojiInvalid))
            elif retcode == 2:
                await message.add_reaction(str(self.config.commands_emojiFailure))


async def main():
    kmra = Klaimera()

    try:
        await kmra.bootstrap()
        await kmra.start(str(kmra.config.user_token))

    except Exception as exc:
        logger.fatal("Error initalising the bot", exc=exc)

    else:
        await kmra.config.file.close()
        exit(0)


if __name__ == "__main__":
    install()
    run(main())
