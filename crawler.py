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
from pyquery import PyQuery
import bs4
from bs4 import BeautifulSoup
from tornado.log import LogFormatter
from requests_html import HTML, Element


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

        self.start_url = "https://xiaoxue.hujiang.com/xiaoxueywjc/"
        self.url_domain =  "https://xiaoxue.hujiang.com/"

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
        except Exception as ex:
            print(ex)
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
            return HTML(html=response.text, url=url)

    def process_html(self, html, task):
        url = task["url"]
        self.url_filter.add(url)
        self.extract_links(html, task)
        self.extract_content(html, task)

    def extract_links(self, html, task):
        # 抽取链接 加到爬取任务列表
        if task['depth'] == 0:
            html = html.find('.module_summary', first=True)
        if task['depth'] == 1:
            html = html.find('.module_summary', first=True)
        if task['depth'] == 2:
            html = html.find("#in_list_main > table > tr:nth-child(6)", first=True)
        if task['depth'] == 3:
            return
        
        for link, text in self.get_absolute_links(html):
            if link.startswith(self.url_domain):
                if link not in self.url_filter:
                    self.url_filter.add(link)
                    new_task = {
                        "url": link,
                        "depth": task["depth"] + 1,
                        "text": text,
                        "parent": task,
                    }
                    self.tasks.append(new_task)

    def get_absolute_links(self, html):
        for a in html.find('a'):
            try:
                href = a.attrs['href'].strip()
                if href and not (href.startswith('#') and html.skip_anchors) and not href.startswith(('javascript:', 'mailto:')):
                    yield html._make_absolute(href), a.full_text
            except KeyError:
                    pass

    def extract_content(self, html, task):
        if task['depth'] == 3:
            article = html.find('#article', first=True)
            content_list = []
            print(article.text)
            for child in article.pq('#article').children():
                print("hehe")
                i = Element(element=child, url=html.url, default_encoding=html.encoding)
                print(i)
                # print(dir(i))
                # print(i.items())
                # break
                print(i.attrs)
                if 'class' in i.attrs and 'clear' in i.attrs['class']:
                    break
                else:
                    content_list.append(i.full_text)
            print(content_list)
            raise Exception()


if __name__ == "__main__":
    crawler = Crawler()
    crawler.start()
