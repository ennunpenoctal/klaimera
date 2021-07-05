from typing import Optional
import logging

from kutils import rie

logger = logging.getLogger("klaimera")

# TODO: Actually log using logger
def log(l: str, m: str, e: Optional[Exception] = None) -> None:
    from traceback import print_tb

    ep = f" ({e.__class__.__name__}: {e})" if e else ""

    print(f"[{l}] {m}" + ep)

    if e:
        print_tb(e.__traceback__)


@rie
def vomit(message: str = "", exc: Optional[Exception] = None) -> None:
    log("VOMIT", message, exc)


@rie
def debug(message: str = "", exc: Optional[Exception] = None) -> None:
    log("DEBUG", message, exc)


@rie
def info(message: str = "", exc: Optional[Exception] = None) -> None:
    log("INFO ", message, exc)


@rie
def warn(message: str = "", exc: Optional[Exception] = None) -> None:
    log("WARN ", message, exc)


@rie
def fatal(message: str = "", exc: Optional[Exception] = None) -> None:
    log("FATAL", message, exc)
