from typing import Callable, NamedTuple, List, Union, Optional
from datetime import datetime, timedelta
from statistics import median
from random import uniform
from bisect import insort
from enum import Enum
from time import time

from asyncio import run, sleep, get_event_loop
from uvloop import install
import asteval  # type: ignore
import discord

import klogging
import kutils

MUDAE_AID = 432610292342587392
KLAIMERA_START = time()
aeval = asteval.Interpreter()
logger = klogging


class EventType(Enum):
    RELOAD = 0
    ROLL = 1
    RESET_CLAIM = 2.0
    RESET_KAKERA = 2.1
    RESET_DAILY = 2.2
    RESET_VOTE = 2.3
    TIME_SYNC = 3
    EVENTMGR_BENCH = 4


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
    async def command_config(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        return 2

    async def command_dispatch(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        if args:
            base, sarg = args.split(" ", 1)

            return 2

        else:
            event_list = "TYPE"

            for event in self.eventmgr.events:
                detail_recur = f"is recurring every {event.delta}" if event.recur else "is non-recurring"
                event_at = datetime.fromtimestamp(event.timestamp) 
                event_in = event_at - datetime.now()
                
                event_list += (
                    f"\n{event.type}\n"
                    f" at {event_at}, {event_in} from now\n"
                    f" {detail_recur}\n"
                )

            await message.reply(f"```{event_list}```")

            return -1

    async def command_status(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        return 2

    async def command_notify(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        return 2

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
            return await self.command_config(args, message)

        elif base == "dispatch":
            return await self.command_dispatch(args, message)

        elif base == "notify":
            return await self.command_notify(args, message)

        elif base == "status":
            return await self.command_status(args, message)

        else:
            return 1

    async def event_reloader(self):
        if self.config.file_mtime != self.config.last_modified():
            try:
                await self.config.load()

            except Exception as exc:
                await logger.warn("Unsuccessful config reload", exc=exc)

    async def event_benchmark(self):
        await self.eventmgr.benchmark()
        await logger.info(
            f"Benchedmarked EventManager, with {self.eventmgr.overhead} overhead"
        )

    async def bootstrap(self):
        self.eventmgr = EventManager()
        await self.eventmgr.benchmark()

        loop = get_event_loop()
        loop.create_task(self.eventmgr.dispatcher())

        self.config = kutils.Config()
        await self.config.init()
        await self.config.load()

        await self.eventmgr.dispatch(
            type=EventType.RELOAD,
            call=self.event_reloader,
            at=timedelta(hours=1),
            recur=True,
            delta=timedelta(minutes=30),
        )

        await self.eventmgr.dispatch(
            type=EventType.EVENTMGR_BENCH,
            call=self.event_benchmark,
            at=timedelta(hours=1),
            recur=True,
            delta=timedelta(hours=1),
        )

    async def on_ready(self):
        await logger.info(f"Ready as {self.user}.")

    async def on_message(self, message: discord.Message):
        if (
            message.author.id == self.user.id and message.content.startswith("kmra ")
        ) or (
            message.content == "kmra status"
            and await self.config.get("commands.statusPublic")
        ):
            if (retcode := await self.command_exec(message)) == 0:
                await message.add_reaction(
                    str(await self.config.get("commands.emojiSuccess"))
                )

            elif retcode == 1:
                await message.add_reaction(
                    str(await self.config.get("commands.emojiFailure"))
                )

            elif retcode == 2:
                await message.add_reaction(
                    str(await self.config.get("commands.emojiInvalid"))
                )


async def main():
    kmra = Klaimera()

    print("Klaimera is starting...\n")

    try:
        await kmra.bootstrap()
        await kmra.start(str(await kmra.config.get("user.token")))

    except Exception as exc:
        logger.fatal("Error initalising the bot", exc=exc)

    else:
        await kmra.config.file.close()
        exit(0)


if __name__ == "__main__":
    install()
    run(main())
