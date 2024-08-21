import json
import asyncio
from time import time
from random import randint
from urllib.parse import urlparse, parse_qs, unquote

import aiohttp
#from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.utils.scripts import escape_html
from bot.utils.levels import levels_data, leagues_data
from bot.exceptions import InvalidSession
from .headers import headers


class Tapper:
    def __init__(self, tg_client: Client, lock: asyncio.Lock):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.lock = lock

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('NotBoredPuppies_bot'),
                bot=await self.tg_client.resolve_peer('NotBoredPuppies_bot'),
                platform='android',
                from_bot_menu=False,
                url='https://frontend.router9.xyz/'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {escape_html(error)}")
            await asyncio.sleep(delay=3)

    async def join_telegram(self, data: str, proxy: str | None) -> bool:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)
            
            for dt in data:
                if dt['type'] == 'bot':
                    parsed_url = urlparse(dt['data'])
                    bot_id = parsed_url.path.split('/')[1]
                    query_params = parse_qs(parsed_url.query)
                    ref = query_params.get('start', [None])[0] or query_params.get('startapp', [None])[0]
                    msrf = f"/start {ref}"
                    chat_id = bot_id
                    await self.tg_client.send_message(bot_id, msrf, disable_notification=True)

                if dt['type'] == 'chat':
                    chat_id = dt['data']
                    await self.tg_client.join_chat(dt['data'])

                logger.success(f"{self.session_name} | Successful Joined | "
                                            f"Type: <c>{dt['type']}</c> (<g>{chat_id}</g>)")
                await asyncio.sleep(delay=2)


            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return True

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Join Telegram: {escape_html(error)}")
            await asyncio.sleep(delay=3)
            return False

    async def login(self, http_client: aiohttp.ClientSession, tg_web_data: str) -> tuple[dict[str], str]:
        try:
            http_client.headers['Telegram-Data'] = tg_web_data

            response = await http_client.post(url='https://topcoin-backend-prod.router9.live/api/login?platform=android', json={})
            response.raise_for_status()
            access_token = await response.text()

            http_client.headers["App-Token"] = access_token
            response = await http_client.get('https://topcoin-backend-prod.router9.live/api/getUser')
            response.raise_for_status()

            profile_data = await response.json()

            return profile_data, access_token
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Login: {escape_html(error)} | "
                         f"Response text: {escape_html(response.text)}...")
            await asyncio.sleep(delay=3)

            return {}, ''

    async def get_profile_data(self, http_client: aiohttp.ClientSession) -> dict[str]:
        try:
            response = await http_client.get('https://topcoin-backend-prod.router9.live/api/getUser')
            response.raise_for_status()

            response_json = await response.json()

            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting Profile Data: {error}")
            await asyncio.sleep(delay=3)

    async def get_spin_result(self, http_client: aiohttp.ClientSession) -> dict[str]:
        try:
            response = await http_client.get('https://topcoin-backend-prod.router9.live/api/getSpinResult')
            response.raise_for_status()

            response_json = await response.json()

            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting Spin Data: {error}")
            await asyncio.sleep(delay=3)

    async def apply_boost(self, http_client: aiohttp.ClientSession, boost_type: str) -> bool:
        response_text = ''
        try:
            response = await http_client.post(url=f'https://topcoin-backend-prod.router9.live/api/{boost_type}',
                                              json={})
            response_text = await response.text()
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Apply {boost_type} Boost: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

            return False

    async def upgrade_boost(self, http_client: aiohttp.ClientSession, boost_type: str) -> bool:
        response_text = ''
        try:
            response = await http_client.post(url=f'https://topcoin-backend-prod.router9.live/api/{boost_type}',
                                              json={})
            response_text = await response.text()
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Upgrade {boost_type} Boost: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

            return False

    async def claim_league_reward(self, http_client: aiohttp.ClientSession, league: str) -> bool:
        try:
            response = await http_client.post(url=f'https://topcoin-backend-prod.router9.live/api/claimLeagueTask',
                                              json={'league': league})
            response.raise_for_status()

            return True
        except Exception as error:
            await asyncio.sleep(delay=1)
            return False

    async def send_taps(self, http_client: aiohttp.ClientSession, taps: int, is_turbo: bool, turbo_t: int) -> dict[str]:
        response_text = ''
        try:
            initTimestamp = int(time() * 1000) - 500
            json_data = {'tapsInc': taps, 'initTimestamp': initTimestamp}

            if is_turbo:
                json_data['tappingGuruEnded'] = True
                json_data['initTimestamp'] = turbo_t

            response = await http_client.post(url='https://topcoin-backend-prod.router9.live/api/tap', json=json_data)
            response_text = await response.text()
            response.raise_for_status()

            response_json = await response.json()

            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Tapping: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

    async def task_handler(self, http_client: aiohttp.ClientSession, id: str, task_type: str) -> str:
        try:
            if task_type in ['startMission', 'finishMission']:
                payload = {"missionId":int(id)}

            if task_type in ['startTask', 'checkTask']:
                payload = {"taskId":int(id)}

            response = await http_client.post(url=f'https://topcoin-backend-prod.router9.live/api/{task_type}', json=payload)
            response.raise_for_status()

            if response.status == 200:
                if task_type == 'checkTask':
                    response_json = await response.json()
                    return {'status': response_json['status']}
                else:
                    return {'status': 'ok'}
            else:
                return {'status': 'error'}
                    
        except Exception as error:
            #logger.error(f"{self.session_name} | Unknown error while task request: {error}")
            await asyncio.sleep(delay=3)
            return {'status': 'error'}

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {escape_html(error)}")

    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        turbo_time = 0
        active_turbo = False
        turbo_taps = 0

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    if time() - access_token_created_time >= 1800:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        profile_data, access_token = await self.login(http_client=http_client, tg_web_data=tg_web_data)

                        if not access_token:
                            continue

                        http_client.headers["App-Token"] = access_token

                        access_token_created_time = time()

                        if settings.CLAIM_TASKS is True:
                            data_list = []
                            for mission in profile_data['missions']:
                                m_id = mission["id"]
                                m_title = mission["name"]

                                if mission["status"] == 0:
                                    resp = await self.task_handler(http_client=http_client, id=m_id, task_type='startMission')
                                    if resp['status'] == 'ok':
                                        for task in mission['tasks']:
                                            t_id = task['id']
                                            if task['status'] == 0:
                                                resp = await self.task_handler(http_client=http_client, id=t_id, task_type='startTask')
                                                if resp['status'] == 'ok':
                                                    if task.get('chatId'):
                                                        data_list.append({'type':'chat','data': task['chatId']})
                                                    if task['type'] == 2:
                                                        data_list.append({'type':'bot','data': task['url']})

                                                    resp = await self.task_handler(http_client=http_client, id=t_id, task_type='checkTask')
                                                    if resp['status'] == 'wait':
                                                        continue
                                
                                if mission["status"] == 1:
                                    for task in mission['tasks']:
                                        t_id = task['id']
                                        t_reward = task['reward']
                                        if task['status'] in [0, 1]:
                                            if task['status'] == 0:
                                                resp = await self.task_handler(http_client=http_client, id=t_id, task_type='startTask')
                                                if resp['status'] == 'error':
                                                    continue
                                                
                                            if task.get('chatId'):
                                                data_list.append({'type':'chat','data': task['chatId']})
                                            if task['type'] == 2:
                                                data_list.append({'type':'bot','data': task['url']})

                                            resp = await self.task_handler(http_client=http_client, id=t_id, task_type='checkTask')
                                            if resp['status'] == 'wait':
                                                continue

                                        if task['status'] == 3:
                                            resp = await self.task_handler(http_client=http_client, id=t_id, task_type='checkTask')
                                            if resp['status'] == 'ok':
                                                continue

                                    resp = await self.task_handler(http_client=http_client, id=m_id, task_type='finishMission')
                                    if resp['status'] == 'ok':
                                        logger.success(f"{self.session_name} | Successful Claim Mission | "
                                                f"Task Title: <c>{m_title}</c> (<g>+{t_reward:,}</g>)")
                                        continue

                            if data_list:
                                status = await self.join_telegram(data=data_list, proxy=proxy)
                                if status:
                                    logger.success(f"{self.session_name} | Successful Joined all bots and chats")

                        balance = profile_data['balance']
                        spins = profile_data['spins']

                        if profile_data['leaguesTasks']:
                            league = profile_data['leaguesTasks'][0]
                            status = await self.claim_league_reward(http_client=http_client, league=league)
                            if status:
                                logger.success(f"{self.session_name} | Successfully claim league <m>{league}</m> reward: (<g>+{leagues_data[league]}</g>)")

                        if spins > 0:
                            logger.info(f"{self.session_name} | You have <m>{spins}</m> spins")
                            while spins > 0:
                                spinResult = await self.get_spin_result(http_client=http_client)
                                if spinResult:
                                    logger.success(f"{self.session_name} | Successfully claim spins <m>{spinResult['item']}</m> reward: (<g>+{spinResult['amount']}</g>) | next claim in 3 sec")
                                    spins -= 1
                                    await asyncio.sleep(delay=3)

                        tap_prices = {index + 1: data['price'] for index, data in
                                    enumerate(levels_data['conf']['tap_levels'])}
                        energy_prices = {index + 1: data['price'] for index, data in
                                        enumerate(levels_data['conf']['energy_levels'])}
                        charge_prices = {index + 1: data['price'] for index, data in
                                        enumerate(levels_data['conf']['charge_levels'])}

                    taps = randint(a=settings.RANDOM_TAPS_COUNT[0], b=settings.RANDOM_TAPS_COUNT[1])

                    if active_turbo:
                        taps += settings.ADD_TAPS_ON_TURBO
                        turbo_taps += taps
                        remainingTime = time() - turbo_time
                        if remainingTime > 20:
                            tap_data = await self.send_taps(http_client=http_client, taps=taps, is_turbo=True, turbo_t=int(turbo_time * 1000) - 500)
                            active_turbo = False
                            turbo_time = 0
                            turbo_taps = 0
                        else:
                            logger.success(f"{self.session_name} | Saved Turbo Taps | "
                                f"Taps: <c>{turbo_taps:,}</c> (<g>+{taps:,}</g>) | Remaining Time: <e>{int(20 - remainingTime):,}</e>")
                    else:
                        tap_data = await self.send_taps(http_client=http_client, taps=taps, is_turbo=False, turbo_t=0)

                    if not tap_data:
                        continue

                    if active_turbo is False:

                        player_data = await self.get_profile_data(http_client=http_client)

                        available_energy = player_data['energy']
                        new_balance = player_data['balance']
                        calc_taps = abs(new_balance - balance)
                        balance = new_balance
                        score = player_data['score']

                        turbo_boost_count = player_data['tappingGuruLeft']
                        energy_boost_count = player_data['fullTankLeft']

                        next_tap_level = player_data['multitap'] + 1
                        next_energy_level = player_data['energyLimit'] + 1
                        next_charge_level = player_data['rechargingSpeed'] + 1

                        logger.success(f"{self.session_name} | Successful tapped! | "
                                    f"Balance: <c>{balance:,}</c> (<g>+{calc_taps:,}</g>) | Score: <e>{score:,}</e>")

                        if (energy_boost_count > 0
                                and available_energy < settings.MIN_AVAILABLE_ENERGY
                                and settings.APPLY_DAILY_ENERGY is True):
                            logger.info(f"{self.session_name} | Sleep 5s before activating the daily energy boost")
                            await asyncio.sleep(delay=5)

                            status = await self.apply_boost(http_client=http_client, boost_type="fullTank")
                            if status is True:
                                logger.success(f"{self.session_name} | Energy boost applied")

                                await asyncio.sleep(delay=1)

                            continue

                        if turbo_boost_count > 0 and settings.APPLY_DAILY_TURBO is True:
                            logger.info(f"{self.session_name} | Sleep 5s before activating the daily turbo boost")
                            await asyncio.sleep(delay=5)

                            status = await self.apply_boost(http_client=http_client, boost_type="tappingGuru")
                            if status is True:
                                logger.success(f"{self.session_name} | Turbo boost applied")

                                await asyncio.sleep(delay=1)

                                active_turbo = True
                                turbo_time = time()

                            continue

                        if (settings.AUTO_UPGRADE_TAP is True
                                and balance > tap_prices.get(next_tap_level, 0)
                                and next_tap_level <= settings.MAX_TAP_LEVEL):
                            logger.info(f"{self.session_name} | Sleep 5s before upgrade tap to {next_tap_level} lvl")
                            await asyncio.sleep(delay=5)

                            status = await self.upgrade_boost(http_client=http_client, boost_type="multitap")
                            if status is True:
                                logger.success(f"{self.session_name} | Tap upgraded to {next_tap_level} lvl")

                                await asyncio.sleep(delay=1)

                            continue

                        if (settings.AUTO_UPGRADE_ENERGY is True
                                and balance > energy_prices.get(next_energy_level, 0)
                                and next_energy_level <= settings.MAX_ENERGY_LEVEL):
                            logger.info(
                                f"{self.session_name} | Sleep 5s before upgrade energy to {next_energy_level} lvl")
                            await asyncio.sleep(delay=5)

                            status = await self.upgrade_boost(http_client=http_client, boost_type="energyLimit")
                            if status is True:
                                logger.success(f"{self.session_name} | Energy upgraded to {next_energy_level} lvl")

                                await asyncio.sleep(delay=1)

                            continue

                        if (settings.AUTO_UPGRADE_CHARGE is True
                                and balance > charge_prices.get(next_charge_level, 0)
                                and next_charge_level <= settings.MAX_CHARGE_LEVEL):
                            logger.info(
                                f"{self.session_name} | Sleep 5s before upgrade charge to {next_charge_level} lvl")
                            await asyncio.sleep(delay=5)

                            status = await self.upgrade_boost(http_client=http_client, boost_type="rechargingSpeed")
                            if status is True:
                                logger.success(f"{self.session_name} | Charge upgraded to {next_charge_level} lvl")

                                await asyncio.sleep(delay=1)

                            continue

                        if available_energy < settings.MIN_AVAILABLE_ENERGY:
                            random_sleep = randint(settings.SLEEP_BY_MIN_ENERGY[0], settings.SLEEP_BY_MIN_ENERGY[1])

                            logger.info(f"{self.session_name} | Minimum energy reached: {available_energy}")
                            logger.info(f"{self.session_name} | Sleep {random_sleep:,}s")

                            await asyncio.sleep(delay=random_sleep)

                            continue

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {escape_html(error)}")
                    await asyncio.sleep(delay=3)

                else:
                    sleep_between_clicks = randint(a=settings.SLEEP_BETWEEN_TAP[0], b=settings.SLEEP_BETWEEN_TAP[1])

                    if active_turbo is True:
                        sleep_between_clicks = 4

                    logger.info(f"Sleep {sleep_between_clicks}s")
                    await asyncio.sleep(delay=sleep_between_clicks)


async def run_tapper(tg_client: Client, proxy: str | None, lock: asyncio.Lock):
    try:
        await Tapper(tg_client=tg_client, lock=lock).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
