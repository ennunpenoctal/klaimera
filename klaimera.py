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
logger = klogging


class EventType(Enum):
    RELOAD = 0
    ROLL = 1
    RESET_CLAIM = 2
    RESET_KAKERA = 3
    TIME_SYNC = 4
    EVENTMGR_BENCH = 5


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
        elif isinstance(at, datetime):
            timestamp = int(at.timestamp())
        else:
            timestamp = at

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

        print(base, args)

        if base == "config":
            # kmra config targets.character add "Yuki Nagato"
            #      <base> <0--------------- 1-- 2------------
            if args and len(sarg := args.split(" ")) >= 1:
                if len(sarg) == 1:
                    if sarg[0] == "reload":
                        await self.config.load()
                        await logger.info("Reloaded configuration")

                        warn_message_str = "\n".join(
                            [f"    {mesg}" for mesg in self.config.commands_warnMessage]
                        )

                        await message.reply(
                            (
                                "```toml"
                                "\n[user]\n"
                                f"notify = {self.config.user_notify}\n"
                                f"sound = {self.config.user_sound}\n"
                                "\n[commands]\n"
                                f"enable       = {self.config.commands_enable}\n"
                                f"status       = {self.config.commands_status}\n"
                                f"config       = {self.config.commands_config}\n"
                                f"dispatch     = {self.config.commands_dispatch}\n"
                                f"notify       = {self.config.commands_notify}\n"
                                f"log          = {self.config.commands_log}\n"
                                f"emoji        = {self.config.commands_emoji}\n"
                                f"emojiSuccess = {self.config.commands_emojiSuccess}\n"
                                f"emojiFailure = {self.config.commands_emojiFailure}\n"
                                f"emojiInvalid = {self.config.commands_emojiInvalid}\n"
                                f"warnMessage  = [\n"
                                f"{warn_message_str}"
                                "]\n"
                                "\n[dispatch.roll]\n"
                                "\n[dispatch.claim]\n"
                                "\n[target]\n"
                                "\n[server]\n"
                                "\n[server.settings]\n"
                                "```"
                            )
                        )

                    else:
                        ...
                        return 0

                elif len(sarg) == 3:
                    ...
                    return 0

                else:
                    return 1

            elif not args:
                ...
                return 0

            else:
                return 1

        if base == "dispatch":
            # kmra dispatch roll 0
            if args is None:
                await message.reply(str(self.eventmgr.events))

            elif len(sarg := args.split(" ")) == 2:
                ...
                return 0

            else:
                return 1

        if base == "notify":
            if args == "push":
                ...
                return 0

            elif args == "sound":
                ...
                return 0

            else:
                return 1

        if base == "log":
            if args and ":" in args:
                ...
                return 0

            elif args == "save":
                ...
                return 0

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
                    await logger.warn("Unsuccessfull config reload", exc=exc)

        await self.eventmgr.dispatch(
            type=EventType.ROLL,
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
