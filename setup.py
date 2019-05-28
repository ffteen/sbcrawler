from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='sbcrawler',
    version='0.1.2',
    author="ffteen",
    author_email="ffteen@qq.com",
    py_modules=['sbcrawler'],
    description="A light weight crawler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ffteen/sbcrawler",
    install_requires=[
        'tornado',
        'requests',
        'requests_html'
    ],
)