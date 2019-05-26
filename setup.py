from setuptools import setup

setup(
    name='sbcrawler',
    version='0.1.0',
    py_modules=['sbcrawler'],
    install_requires=[
        'tornado',
        'requests',
        'requests_html'
    ],
)