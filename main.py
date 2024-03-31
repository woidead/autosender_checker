import asyncio
from datetime import datetime
import requests
import logging
import os
import sys
from random import shuffle, uniform


import schedule
import socks
from telethon.tl.types import User

from opentele.api import API, UseCurrentSession
from opentele.td import TDesktop

from config import (proxy_type, chats, timeout, message, interval)

log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"{log_directory}/log_{current_time}.log"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_filename),
                        logging.StreamHandler()
                    ])


class Proxy:
    """Класс для работы с прокси."""

    def __init__(self):
        self.proxy_type = int(proxy_type)
        self.index = 0

    def fetch_proxy_from_link(self, link):
        proxies = requests.get(link)
        proxy = proxies.text.split("\n")[self.index].split(":")
        addr, port, login, password = \
            proxy[0], proxy[1], proxy[2], proxy[3]
        return addr, int(port), login, password

    def get_proxy(self):
        logging.info(f"proxy type {self.proxy_type}")
        if self.proxy_type == 0:
            link = open("proxy.txt", "r").read().strip()
            return self.fetch_proxy_from_link(link)
        elif self.proxy_type == 1:
            proxies = open("proxy.txt", "r").read().split("\n")
            proxy = proxies[self.index].split(":")
            addr, port, login, password = \
                proxy[0], proxy[1], proxy[2], proxy[3]
            return addr, int(port), login, password
        else:
            return "", "", "", ""


async def authorize(tname):
    try:
        tdesk = TDesktop(f"tdatas/{tname}")
    except Exception as e:
        logging.error(f"Невозможно создать tdesk!: {e}")
        sys.exit(1)

    api = API.TelegramIOS.Generate()
    prox = Proxy()
    addr, port, username, password = prox.get_proxy()

    if addr == "" or port == "":
        logging.warning(f"{tname} | Авторизация без прокси")
        try:
            client = await tdesk.ToTelethon(
                f"sessions/{tname}.session",
                UseCurrentSession,
                api,
            )
            await client.connect()
        except Exception as e:
            logging.error(f"Неудалось авторизоваться в аккаунт без прокси!: {e}")
            return
    else:
        proxy_conn = (socks.SOCKS5, addr, int(port), True, username, password)
        logging.info(f"{tname} | Прокси: {addr}:{port}:{username}:{password}")
        logging.info(f"{tname} | Авторизация")
        try:
            client = await tdesk.ToTelethon(
                f"sessions/{tname}.session",
                UseCurrentSession,
                api,
                proxy=proxy_conn,
                connection_retries=0,
                retry_delay=1,
                auto_reconnect=True,
                request_retries=0,
            )
            await client.connect()
        except Exception as e:
            if "ConnectionError" in str(e):
                logging.warning(f"{tname} | Нерабочие прокси: {addr}:{port}:{username}:{password}")
                logging.info(f"{tname} | Заменяем прокси")
                return authorize(tname)
            else:
                logging.error(f"Неудалось авторизоваться с прокси: {e}")
                await client.disconnect()
                return

    return client


async def send_msg(client, chat_id, message):
    try:
        await client.delete_dialog(chat_id, revoke=True)
        logging.info(f"История чата с {chat_id} удалена.")
        await client.send_message(chat_id, message)
        logging.info(f"Сообщение '{message}' отправлено в чат {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения в send_msg в чат {chat_id}: {e}")


async def check_all_messages(client):
    checks = {chat: "No response" for chat in chats}
    try:
        dialogs = await client.get_dialogs(limit=10)
        await asyncio.sleep(round(uniform(1, 3), 2))
        for dialog in dialogs:
            if isinstance(dialog.entity, User) and dialog.entity.username in chats:
                if dialog.unread_count > 0:
                    logging.info(f"Есть непрочитанные сообщения от {dialog.entity.username}.")
                    checks[str(dialog.entity.username)] = True
                    await asyncio.sleep(round(uniform(1, 3), 2))
                else:
                    checks[str(dialog.entity.username)] = False
        return checks
    except Exception as e:
        logging.error(f"Ошибка при get_dialogs в check_all_messages: {e}")


async def main(tdataname):
    shuffle(chats)
    try:
        client = await authorize(tdataname)
        await asyncio.sleep(round(uniform(1, 3), 2))
    except Exception as e:
        logging.error(f"Ошибка при создании client в main: {e}")
    for chat in chats:
        try:
            await send_msg(client, chat, message)
            logging.info(f"Оправлено сообщение в {chat}")
            await asyncio.sleep(round(uniform(1, 3), 2))
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения в main: {e}")
        await asyncio.sleep(timeout)
    await asyncio.sleep(10)
    try:
        await client.send_message('woidead', str(await check_all_messages(client)))
        logging.info(await check_all_messages(client))
    except Exception as e:
        logging.error(f"Ошибка при отправке отчета: {e}")
    await client.disconnect()


async def start():
    try:
        os.remove("./tdatas/.gitkeep")
    except Exception:
        pass
    tdataname = os.listdir("./tdatas")[0]
    logging.info(f"{'tdatas'}/{tdataname} working")
    schedule.every(interval).hours.do(lambda: asyncio.create_task(main(tdataname=tdataname)))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)
asyncio.run(start())
