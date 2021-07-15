from typing import Optional
from inspect import stack
from pathlib import Path
from time import time

import aiofiles
import traceback


class Logger:
    level_map = {
        0: "DEBUG",
        1: "INFO",
        2: "WAIFU",
        3: "ERROR",
        4: "WARN",
        5: "FATAL",
    }

    def __init__(self):
        self.log_file_path = (
            Path(__file__).absolute().parent.joinpath(f"logs/{int(time())}.log")
        )

        self.log_level = -1
        self.log_history = []
        self.log_history_max = 100

        if not self.log_file_path.parent.exists():
            try:
                self.log_file_path.parent.mkdir()

            except Exception as e:
                print(
                    f"Could not make log directory {self.log_file_path}."
                    f"\n\n{e.__class__.__name__}: {e}"
                )
                traceback.print_tb(e.__traceback__)
                exit(-1)

    async def log(self, text: str, level: int = 1, exc: Exception = None) -> None:
        if level < self.log_level:
            return None

        if not self.log_file_path.exists():
            self.log_file = await aiofiles.open(self.log_file_path, "w")

        ctime = f"{time():.2f}"

        try:
            _stack = stack()
            caller = f"{_stack[2].frame.f_code.co_name}"

        except Exception:
            caller = ""

        finally:
            del _stack

        if "\n" in text:
            _text = text.split("\n")
            text = _text[0]

        else:
            _text = []

        header = f"[{self.level_map[level]} {caller} {ctime}]"

        if exc:
            mesg = f"{header} {text} <- {exc.__class__.__name__}: {exc}\n"
        else:
            mesg = f"{header} {text}"

        print(mesg)
        await self.log_file.write(mesg + "\n")
        self.log_history.append(mesg)

        if _text:
            padding = len(header)

            for line in _text[1:]:
                print(f"{padding}{line}")
                await self.log_file.write(_lmesg := f"{padding}{line}\n")
                self.log_history.append(_lmesg)

        if exc:
            tb_text = traceback.format_exception(None, exc, exc.__traceback__)
            await self.log_file.write(f"{exc.__class__.__name__}: {exc}\n")
            for line in tb_text:
                await self.log_file.write(f"{line}\n")

        await self.log_file.flush()

        if len(self.log_history) > self.log_history_max:
            self.log_history = self.log_history[-self.log_history_max :]

    async def debug(self, message: str, exc: Optional[Exception] = None) -> None:
        await self.log(message, level=0, exc=exc)

    async def info(self, message: str, exc: Optional[Exception] = None) -> None:
        await self.log(message, level=1, exc=exc)

    async def waifu(self, message: str, exc: Optional[Exception] = None) -> None:
        await self.log(message, level=2, exc=exc)

    async def error(self, message: str, exc: Optional[Exception] = None) -> None:
        await self.log(message, level=3, exc=exc)

    async def warn(self, message: str, exc: Optional[Exception] = None) -> None:
        await self.log(message, level=4, exc=exc)

    async def fatal(self, message: str, exc: Optional[Exception] = None) -> None:
        await self.log(message, level=5, exc=exc)


logger = Logger()
