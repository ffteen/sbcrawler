# -*- coding: utf-8 -*-

from collections import deque
import sys
import json
import time
import os
import random
from urllib.parse import urljoin

import tqdm
import requests
from pathlib import Path

import bs4
from bs4 import BeautifulSoup
from tornado.log import LogFormatter


import logging


class Crawler:

    user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

    _log_instance = None

    name = "Crawler"

    log_level = logging.INFO

    sleep_interval_range = (1, 1)

    output_dir = ""

    @property
    def log(self):
        if self.__class__._log_instance is None:
            _log = logging.getLogger(self.name)
            _log.setLevel(self.log_level)
            _log.propagate = False

            _log_handler = logging.StreamHandler()
            _log_formatter = LogFormatter()
            _log_handler.setFormatter(_log_formatter)

            _log.addHandler(_log_handler)
            self.__class__._log_instance = _log

        return self.__class__._log_instance

    def get_sleep_interval(self):
        left, right = self.sleep_interval_range
        return random.randint(left * 1000, right*1000) / 1000

    def __init__(self):
        self.tasks = deque()
        self.url_filter = set()

        self.start_url = ""
        self.url_domain =  ""

        self.download_error_urls = []   # 下载出错的地址
        self.process_error_urls = []    # 解析、提取内容等方面出错的地址

        self.need_dump_tasks = False
        self.current_task = None

    def start(self):
        path = Path(os.path.join(self.output_dir, ".crawl", "task.json"))
        if path.is_file():
            with path.open(encoding='utf-8') as f:
                d = json.load(f)
                self.url_filter = set(d["url_filter"])
                self.tasks.extend(d["tasks"])
            path.unlink()
        else:
            task = {
                "url": self.start_url,
                "depth": 0,
                "parent": None,
            }
            self.tasks.append(task)

        try:
            while self.tasks:
                self.current_task = self.tasks.popleft()
                html = self.download_html(self.current_task)
                self.process_html(html, self.current_task)
                self.current_task = None
                time.sleep(self.get_sleep_interval())
        except KeyboardInterrupt:
            self.need_dump_tasks = True
        except Exception:
            self.need_dump_tasks = True
            if self.current_task:
                self.tasks.appendleft(self.current_task)
                self.url_filter.remove(self.current_task['url'])

        self.atexit()


    def atexit(self):
        status_path = os.path.join(self.output_dir, ".crawl")

        if self.need_dump_tasks:
            os.makedirs(status_path, exist_ok=True)
            with open(os.path.join(status_path, 'task.json'), 'w', encoding='utf-8') as f:
                d = {
                    "tasks": list(self.tasks),
                    "url_filter": list(self.url_filter),
                }
                json.dump(d, f)

        if self.download_error_urls:
            os.makedirs(status_path, exist_ok=True)
            with open(os.path.join(status_path, 'download_error.txt'), 'w', encoding='utf-8') as f:
                for link in self.download_error_urls:
                    f.write(link + '\n')

        if self.process_error_urls:
            os.makedirs(status_path, exist_ok=True)
            with open(os.path.join(status_path, 'process_error.txt'), 'w', encoding='utf-8') as f:
                for link in self.process_error_urls:
                    f.write(link + '\n')

    def download_html(self, task):
        headers = {
            "User-Agent": self.user_agent
        }
        url = task["url"]
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.download_error_urls.append(url)
            self.log.warning(f"抓取[{url}]异常，status_code={response.status_code}")
        else:
            self.log.info(f"抓取[{url}]正常，status_code={response.status_code}")
            return response.text

    def process_html(self, html, task):
        url = task["url"]
        self.url_filter.add(url)

        soup = BeautifulSoup(html, features='lxml')

        self.extract_links(soup, task)
        self.extract_content(soup, task)

    def extract_links(self, soup, task):
        # 抽取链接 加到爬取任务列表
        if task['depth'] == 0:
            soup = soup.find('div', class_="module_summary")
        if task['depth'] == 1:
            soup = soup.find('div', class_="module_summary")
        if task['depth'] == 2:
            soup = soup.select("#in_list_main > table > tr:nth-child(6)")[0]
        if task['depth'] == 3:
            return
        for a in soup.find_all('a', href=True):
            link = urljoin(task['url'], a['href'])
            if link.startswith(self.url_domain):
                if link not in self.url_filter:
                    self.url_filter.add(link)
                    new_task = {
                        "url": link,
                        "depth": task["depth"] + 1,
                        "text": a.get_text().strip(),
                        "parent": task,
                    }
                    self.tasks.append(new_task)

    def extract_content(self, soup, task):
        if task['depth'] == 3:
            print(task)
            s = soup.find('div', id='article')
            content_list = []
            for i in s.children:
                if hasattr(i, "attrs"):
                    if 'class' in i.attrs and 'clear' in i.attrs['class']:
                        break
                elif isinstance(i, bs4.Tag):
                    content_list.append(i.strings)
                elif isinstance(i, str):
                    content_list.append(i)
            print(content_list)
            raise Exception()


if __name__ == "__main__":
    crawler = Crawler()
    crawler.start()
