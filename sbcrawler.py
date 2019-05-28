# -*- coding: utf-8 -*-

from collections import deque

import os
import sys
import json
import time
import random
import pathlib

import requests

from tornado.log import LogFormatter
from requests_html import HTML, Element

import logging


class Link:

    def __init__(self, url, anchor_text=""):
        self.url = url
        self.anchor_text = anchor_text

    @property
    def text(self):                    # anchor_text名字太长了,起个短点的别名
        return self.anchor_text


class Task:

    def __init__(self, link: Link, parent=None, depth=None):
        self.link = link
        self.parent = parent
        self._depth = depth
    
    @property
    def url(self):
        return self.link.url

    @property
    def depth(self):
        if self._depth is None:
            if self.parent:
                self._depth = self.parent.depth + 1
            else:
                self._depth = 0
        return self._depth
    
    @property
    def anchor_text(self):
        return self.link.anchor_text

    @property
    def text(self):
        return self.anchor_text

    def to_dict(self):
        d = {
            "url": self.url,
            "anchor_text": self.text,
            "depth": self.depth,
            "parent": self.parent.to_dict() if self.parent else None,
        }
        return d
    
    @classmethod
    def from_dict(cls, dic):
        link = Link(dic["url"], dic["anchor_text"])
        if dic["parent"]:
            parent = cls.from_dict(dic["parent"])
        else:
            parent = None
        return cls(link, parent, dic.get('depth', None))


class Crawler:

    user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

    _log_instance = None

    name = "Crawler"

    log_level = logging.INFO

    sleep = True
    sleep_interval_range = (1, 3)

    output_dir = ""
    output_file = "output.json"

    start_url = ""
    
    allowed_domain = ""

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

        self.download_error_urls = []   # 下载出错的地址
        self.process_error_urls = []    # 解析、提取内容等方面出错的地址

        self.need_dump_tasks = False    # 异常退出时需要把状态保存一下
        self.current_task = None        # 当前下载任务
        self._output_file = None

    def start(self):
        path = pathlib.Path(os.path.join(self.output_dir, ".crawl", "task.json"))
        if path.is_file():
            try:
                with path.open(encoding='utf-8') as f:
                    d = json.load(f)
                    self.url_filter = set(d["url_filter"])
                    for dic in d["tasks"]:
                        self.tasks.append(Task.from_dict(dic))
                path.unlink()
            except Exception as ex:
                self.log.exception('Exception')
                sys.exit(1)
        else:
            link = Link(self.start_url)
            self.tasks.append(Task(link))

        try:
            while self.tasks:
                self.current_task = self.tasks.popleft()
                html = self.download_html(self.current_task)
                if html:
                    self.process_html(html, self.current_task)
                self.current_task = None
                if self.sleep:
                    time.sleep(self.get_sleep_interval())       # sleep一段时间
        except KeyboardInterrupt:
            self.need_dump_tasks = True
            self.log.info('KeyboardInterrupt')
        except Exception as ex:
            self.log.exception('Exception')
            self.need_dump_tasks = True
            if self.current_task:
                self.tasks.appendleft(self.current_task)
                self.url_filter.remove(self.current_task.url)
            
        self.atexit()

    def atexit(self):
        status_path = os.path.join(self.output_dir, ".crawl")

        if self.need_dump_tasks:
            os.makedirs(status_path, exist_ok=True)
            with open(os.path.join(status_path, 'task.json'), 'w', encoding='utf-8') as f:
                d = {
                    "tasks": [t.to_dict() for t in self.tasks],
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
        response = requests.get(task.url, headers=headers)
        if response.status_code != 200:
            self.download_error_urls.append(task.url)
            self.log.warning(f"download [ {task.url} ] error! status_code={response.status_code}")
            return None
        else:
            self.log.info(f"download [ {task.url} ] success.")
            return HTML(html=response.text, url=task.url)

    def process_html(self, html, task):
        self.url_filter.add(task.url)
        self.extract_links(html, task)
        content = self.extract_content(html, task)
        self.output(content, task)

    def output(self, content, task):
        if not self._output_file:
            fname = os.path.join(self.output_dir, "output.json")
            self._output_file = open(fname, 'a', encoding="utf-8")
        elif content:
            self._output_file.write(json.dumps(content, ensure_ascii=False) + '\n')
        else:
            self.log.info(f'task[{task.url} ] no output')

    def get_absolute_links(self, html):
        for a in html.find('a'):
            try:
                href = a.attrs['href'].strip()
                if href and not (href.startswith('#') and html.skip_anchors) and not href.startswith(('javascript:', 'mailto:')):
                    yield Link(html._make_absolute(href), a.full_text)
            except KeyError:
                    pass
    
    def tasks_append(self, task):
        if task.url not in self.url_filter:
            self.url_filter.add(task.url)
            self.tasks.append(task)
        else:
            self.log.debug(f"filtered url [{task.url} ]")

    def tasks_append_left(self, task):
        if task.url not in self.url_filter:
            self.url_filter.add(task.url)
            self.tasks.appendleft(task)
        else:
            self.log.debug(f"filtered url [{task.url} ]")

    def extract_links(self, html, task):
        for link in self.get_absolute_links(html):
            if link.url.startswith(self.allowed_domain):
                new_task = Task(link, parent=task)
                self.tasks_append(new_task)

    def extract_content(self, html, task):
        raise NotImplementedError
