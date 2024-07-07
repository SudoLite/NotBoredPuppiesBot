import os
import glob
import time
import random
import shutil
import asyncio
import pathlib
from typing import Union

from pyrogram import Client
from pyrogram.types import Message
from better_proxy import Proxy
from multiprocessing import Queue

from bot.config import settings
from bot.utils import logger
from bot.utils.emojis import num, StaticEmoji


def get_session_names() -> list[str]:
    session_names = glob.glob("sessions/*.session")
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names


def get_proxies() -> list[Proxy]:
    if settings.USE_PROXY_FROM_FILE:
        with open(file="bot/config/proxies.txt", encoding="utf-8-sig") as file:
            proxies = [Proxy.from_str(proxy=row.strip()).as_url for row in file]
    else:
        proxies = []

    return proxies


def get_command_args(
        message: Union[Message, str],
        command: Union[str, list[str]] = None,
        prefixes: str = "/",
) -> str:
    if isinstance(message, str):
        return message.split(f"{prefixes}{command}", maxsplit=1)[-1].strip()
    if isinstance(command, str):
        args = message.text.split(f"{prefixes}{command}", maxsplit=1)[-1].strip()
        return args
    elif isinstance(command, list):
        for cmd in command:
            args = message.text.split(f"{prefixes}{cmd}", maxsplit=1)[-1]
            if args != message.text:
                return args.strip()
    return ""


def with_args(text: str):
    def decorator(func):
        async def wrapped(client: Client, message: Message):
            if message.text and len(message.text.split()) == 1:
                await message.edit(f"<emoji id=5210952531676504517>❌</emoji>{text}")
            else:
                return await func(client, message)

        return wrapped

    return decorator


def get_help_text():
    return f"""<b>
{StaticEmoji.FLAG} [Demo version]

{num(1)} /help - Displays all available commands
{num(2)} /tap [on|start, off|stop] - Starts or stops the tapper

</b>"""


async def stop_tasks(client: Client = None) -> None:
    if client:
        all_tasks = asyncio.all_tasks(loop=client.loop)
    else:
        loop = asyncio.get_event_loop()
        all_tasks = asyncio.all_tasks(loop=loop)

    clicker_tasks = [task for task in all_tasks
                     if isinstance(task, asyncio.Task) and task._coro.__name__ == 'run_tapper']

    for task in clicker_tasks:
        try:
            task.cancel()
        except:
            ...


def escape_html(text: str) -> str:
    text = str(text)
    return text.replace('<', '\\<').replace('>', '\\>')
