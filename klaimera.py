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
aeval = asteval.Interpreter()
logger = klogging.Logger()


class EventType(Enum):
    CONFIG_RELOAD = 100
    RESET_CLAIM = 200
    RESET_KAKERA = 201
    RESET_DAILY = 202
    RESET_VOTE = 203
    SYNC_TIME = 300
    EVENTMGR_BENCH = 400
    ROLL = 500


class Event(NamedTuple):
    type: EventType
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
                            f"dispatch, recurs every {event.delta} with next call "
                            f"scheduled for {next_timestamp}."
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
                Event(
                    type=EventType.EVENTMGR_BENCH,
                    timestamp=int(time()),
                    call=empty,
                    recur=False,
                ),
            )

            stime = time()
            await self.dispatcher(bench=True)
            times.append(time() - stime)

        self.overhead = median(times)

    async def dispatch(
        self,
        type: EventType,
        call: Callable,
        at: Union[timedelta, int, datetime],
        recur: bool = False,
        delta: timedelta = timedelta(),
    ) -> None:
        if isinstance(at, timedelta):
            time_info = datetime.now() + at
            timestamp = int(time_info.timestamp())
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

        await logger.info(f"Dispatched {type} for {time_info}{recur_info}")

        insort(
            self.events,
            Event(
                type=type,
                timestamp=timestamp,
                call=call,
                recur=recur,
                delta=delta,
            ),
        )


class Klaimera(discord.Client):
    async def command_config(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        return 2

    async def command_dispatch(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        if args and len(sargs := args.split(" ", 1)) > 1:
            base, sub = sargs

            if base.isnumeric() and (index := int(base)) <= len(self.eventmgr.events):
                ...
                return 0

            elif base.upper() in [event.name for event in EventType]:
                ...
                return 0

            else:
                return 1

        elif not args:
            event_list = ""

            for evindex, event in enumerate(self.eventmgr.events):
                if event.recur:
                    detail_recur = f"is recurring every {event.delta}"
                else:
                    detail_recur = "is non-recurring"

                event_at = datetime.fromtimestamp(event.timestamp)
                event_in = event_at - datetime.now()

                event_list += (
                    f"\n[{evindex}: {event.type.name}]\n"
                    f" at {event_at}, {event_in} from now\n"
                    f" {detail_recur}\n"
                )

            await message.reply(f"```{event_list}```")

            return -1

        else:
            return 1

    async def command_status(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        return 2

    async def command_notify(
        self, args: Optional[str], message: discord.Message
    ) -> int:
        if args and len(sargs := args.split(" ", 1)) >= 1:
            if sargs[0] == "alert":
                return await kutils.alert()

            elif sargs[0] == "push":
                if len(sargs) > 1:
                    pmesg = sargs[1]
                else:
                    pmesg = "Test!"

                return await kutils.notify(pmesg)

            else:
                return 1

        else:
            return 1

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
            f"Benchmarked EventManager, with an overhead of {self.eventmgr.overhead}s"
        )

    async def bootstrap(self):
        # Logger Installation
        kutils.logger = logger

        # Event Manager
        self.eventmgr = EventManager()
        await self.eventmgr.benchmark()
        await logger.info(
            f"Benchmarked EventManager, with an overhead of {self.eventmgr.overhead}s"
        )

        loop = get_event_loop()
        loop.create_task(self.eventmgr.dispatcher())

        # Configuration
        self.config = kutils.Config()
        await self.config.init()
        await self.config.load()

        # Events
        await self.eventmgr.dispatch(
            type=EventType.CONFIG_RELOAD,
            call=self.event_reloader,
            at=timedelta(minutes=30),
            recur=True,
            delta=timedelta(minutes=30),
        )

        await self.eventmgr.dispatch(
            type=EventType.EVENTMGR_BENCH,
            call=self.event_benchmark,
            at=timedelta(minutes=10),
            recur=True,
            delta=timedelta(minutes=10),
        )

    async def roll_parse(self, message: discord.Message):
        embed: discord.Embed = message.embeds[0]
        description: str = embed.description.splitlines()  # type: ignore
        series = description[0]
        kakera = 0

        for line in description:
            if "<:kakera:469835869059153940>" in line:
                try:
                    for sub in line.split("**"):
                        try:
                            kakera = int(sub)

                        except Exception:
                            pass

                except Exception as exc:
                    await logger.warn("?", exc=exc)

        if (
            embed.author.name in await self.config.get("target.roll.character")  # type: ignore
            or series in await self.config.get("target.roll.series")  # type: ignore
            or kakera >= await self.config.get("target.roll.kakera")  # type: ignore
        ):
            wait_min, wait_max = await self.config.get("target.roll.delay")  # type: ignore
            await sleep(uniform(wait_min, wait_max))
            await message.add_reaction("🍞")

        else:
            await logger.waifu(f"Rolled {embed.author.name} <{series}> [{kakera}]")

    async def parse(self, message: discord.Message):
        if (
            await self.config.get("dispatch.claim.auto")
            and len(message.embeds) > 0
            and isinstance(message.embeds[0], discord.Embed)
            and isinstance(message.embeds[0].description, str)
            and isinstance(message.embeds[0].author.name, str)
            and not (
                # TODO: Remove/rework this once kakera claim tracking is implemented
                isinstance(footer := message.embeds[0].footer.text, str)
                and "Belongs to" in footer
            )
            and any(
                [
                    "React with any emoji to claim!" in message.embeds[0].description,
                    "Wished by" in message.content,
                    "<:kakera:469835869059153940>"
                    in message.embeds[0].description.splitlines()[-1],
                ]
            )
        ):
            await self.roll_parse(message)

        elif "are now married!" in message.content:
            await self.claim_parse(message)

    async def claim_parse(self, message: discord.Message):
        bride = message.content.split("**")[3]

        if bride in self.config.get("target.roll.character"):  # type: ignore
            targeted = True

        else:
            targeted = False

        if message.content.split("**")[1] == self.user.name:
            await logger.waifu(mesg := f"Claimed {bride}!")
            await kutils.alert()
            await kutils.notify(mesg)

        elif targeted:
            await logger.waifu(mesg := f"Stolen: {bride}")
            await kutils.alert()
            await kutils.notify(mesg)

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
                    str(await self.config.get("commands.emojiInvalid"))
                )

            elif retcode == 2:
                await message.add_reaction(
                    str(await self.config.get("commands.emojiFailure"))
                )

        if message.author.id == MUDAE_AID:
            await self.parse(message)


async def main():
    kmra = Klaimera()

    print("Klaimera version 0.0.1\n")

    try:
        await kmra.bootstrap()
        await kmra.start(await kmra.config.get("user.token"))  # type: ignore

    except Exception as exc:
        await logger.fatal("Error initalising the bot", exc=exc)

    else:
        await kmra.config.file.close()
        exit(0)


if __name__ == "__main__":
    install()
    run(main())
