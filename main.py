import asyncio
import configparser
import datetime
import logging
import os
import shutil
import sys
import threading
import time
import pytz
import tkinter as tk
from datetime import datetime, timedelta
from random import randint
from threading import Thread
from tkinter import messagebox, ttk

import requests
import sentry_sdk
import socks
from sentry_sdk.integrations.logging import LoggingIntegration
from telethon import TelegramClient, events, sync
from telethon.errors import FloodWaitError
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, User, MessageActionContactSignUp

from opentele.api import API, CreateNewSession, UseCurrentSession
from opentele.td import TDesktop
from opentele.tl import TelegramClient

from config import (proxy_type, chats, timeout)


class Proxy:
        """Класс для работы с прокси."""

        def __init__(self):
            self.proxy_type = int(proxy_type)

        def fetch_proxy_from_link(self, link, index):
            proxies = requests.get(link)
            proxy = proxies.text.split("\n")[index].split(":")
            addr = proxy[0]
            port = proxy[1]
            login = proxy[2]
            password = proxy[3]
            return addr, int(port), login, password

        def get_proxy(self, index):
            logging.warning(f"proxy type {self.proxy_type}")
            if self.proxy_type == 0:
                link = open("proxy.txt", "r").read().strip()
                return self.fetch_proxy_from_link(link, index)
            if self.proxy_type == 1:
                proxies = open("proxy.txt", "r").read().split("\n")
                proxy = proxies[index].split(":")
                addr = proxy[0]
                port = proxy[1]
                login = proxy[2]
                password = proxy[3]
                return addr, int(port), login, password
            if self.proxy_type == 2:
                return "", ""


async def authorize(tname,proxy):
    try:
        tdesk = TDesktop(f"tdatas/{tname}")
    except Exception as e:
        logging.error(f"Невозможно создать tdesk!: {e}")
        sys.exit(1)
    
    api = API.TelegramIOS.Generate()
    prox = Proxy()
    addr, port, username, password = prox.get_proxy(proxy)
    proxy_conn = (socks.SOCKS5, addr, int(port), True, username, password)
    logging.info(f"{tname} | Прокси: {addr}:{port}:{username}:{password}")
    logging.info(f"{tname} | Авторизация")
    try:
        if f"{tname}.session" in os.listdir("sessions/"):
            os.remove(f"sessions/{tname}.session")
    except Exception as e:
        print(e)

    if addr == "" or port == "":
        try:
            client = await tdesk.ToTelethon(
                f"sessions/{tname}.session",
                UseCurrentSession,
                api,
            )
            await client.connect()
        except Exception as e:
            logging.error(f"Неудалось авторизоваться в аккаунт без прокси!{e}")
            return
    else:
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
            sentry_sdk.capture_exception(e)
            if "ConnectionError" in str(e):
                logging.warning(f"{tname} | Нерабочие прокси: {addr}:{port}:{username}:{password}")
                logging.info(f"{tname} | Заменяем прокси")
                return authorize(proxy + 1, tname)
            else:
                logging.error(f"Неудалось авторизоваться с прокси: {e}")
                await client.disconnect()
                return
            
    return client