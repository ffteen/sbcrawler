# sbcrawler
light weight crawler

轻量级的爬虫框架sbcrawler

## 写这个框架的动机

1. 平时写爬虫过程中，发现通常不需要什么高大上的异步、并发、分布式等功能。
2. 小需求对防止被封，中断继续，日志进度等方面有更多重复性的代码。
3. sbcrawler就是实现一个最简单的爬虫框架，让你可以专注于写内容抽取逻辑。

## 特点
- 单进程，非异步
- 断点续爬
- 错误日志记录

## 用法

```python
# -*- coding: utf-8 -*-

from sbcrawler import Crawler

class MyCrawlerExample(Crawler):

    start_url = "https://xxx.xxx.com/xxx/"  # 起始种子url

    allowed_domain =  "https://xxx.xxx.com/"   # 限制域,要带http

    def extract_links(self, html, task):
        # 抽取链接 加到爬取任务列表
        if task.depth == 0 or task.depth == 1:
            html = html.find('.module_summary', first=True)
        if task.depth == 2:
            html = html.find("#in_list_main > table > tr:nth-child(6)", first=True)
        if task.depth == 3:
            return
        
        super().extract_links(html, task)

    def extract_content(self, html, task):
        if task.depth == 3:
            title = html.find('#title', first=True)
            article = html.find('#article', first=True)
            return {'title': title.full_text, 'article': article.full_text}


if __name__ == "__main__":
    crawler = MyCrawlerExample()
    crawler.start()

```


## 安装

暂未在pypi发布
