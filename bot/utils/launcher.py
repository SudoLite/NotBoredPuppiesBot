import asyncio
import argparse
from itertools import cycle

from pyrogram import Client, compose

from bot.config import settings
from bot.utils import logger
from bot.core.tapper import run_tapper
from bot.core.registrator import register_sessions
from bot.utils.scripts import get_session_names, get_proxies

banner = """

888b    888          888    888888b.                                 888 8888888b.                             d8b                   888888b.            888    
8888b   888          888    888  "88b                                888 888   Y88b                            Y8P                   888  "88b           888    
88888b  888          888    888  .88P                                888 888    888                                                  888  .88P           888    
888Y88b 888  .d88b.  888888 8888888K.   .d88b.  888d888 .d88b.   .d88888 888   d88P 888  888 88888b.  88888b.  888  .d88b.  .d8888b  8888888K.   .d88b.  888888 
888 Y88b888 d88""88b 888    888  "Y88b d88""88b 888P"  d8P  Y8b d88" 888 8888888P"  888  888 888 "88b 888 "88b 888 d8P  Y8b 88K      888  "Y88b d88""88b 888    
888  Y88888 888  888 888    888    888 888  888 888    88888888 888  888 888        888  888 888  888 888  888 888 88888888 "Y8888b. 888    888 888  888 888    
888   Y8888 Y88..88P Y88b.  888   d88P Y88..88P 888    Y8b.     Y88b 888 888        Y88b 888 888 d88P 888 d88P 888 Y8b.          X88 888   d88P Y88..88P Y88b.  
888    Y888  "Y88P"   "Y888 8888888P"   "Y88P"  888     "Y8888   "Y88888 888         "Y88888 88888P"  88888P"  888  "Y8888   88888P' 8888888P"   "Y88P"   "Y888 
                                                                                             888      888                                                       
                                                                                             888      888                                                       
                                                                                             888      888                                                       

                                                                || Created By Sudolite ||

"""

options = """
Select an action:

    1. Create session
    2. Run clicker
    3. Run via Telegram (Beta)
"""


global tg_clients


async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    print(banner)

    logger.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")

    action = parser.parse_args().action

    if not action:
        print(options)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ["1", "2", "3"]:
                logger.warning("Action must be 1, 2 or 3")
            else:
                action = int(action)
                break

    if action == 1:
        await register_sessions()
    elif action == 2:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)
    elif action == 3:
        tg_clients = await get_tg_clients()

        logger.info("Send /help command in Saved Messages\n")

        await compose(tg_clients)


async def run_tasks(tg_clients: list[Client]):
    proxies = get_proxies()
    proxies_cycle = cycle(proxies) if proxies else None
    lock = asyncio.Lock()

    tasks = [
        asyncio.create_task(
            run_tapper(
                tg_client=tg_client,
                proxy=next(proxies_cycle) if proxies_cycle else None,
                lock=lock,
            )
        )
        for tg_client in tg_clients
    ]

    await asyncio.gather(*tasks)
