import os
import platform
import subprocess


def copy_selection(title: str, url: str):
    """
    Copy selected bookmark's url to clipboard
    """
    import pyperclip

    pyperclip.copy(url)


def open_selection(title: str, url: str):
    """
    Open selected bookmark's url in default browser
    """
    system = platform.system()
    if system == "Windows":
        os.startfile(url)
        return
    elif system == "Darwin":
        subprocess.Popen(
            ["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return
    # Linux or BSD
    try:
        subprocess.Popen(
            ["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except OSError:
        raise RuntimeError("Cannot open default browser")


async def fetch_html(session, url):
    async with session.get(url, timeout=2) as response:
        return await response.text()


async def parse_page_title(html):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    return soup.title.string


async def async_infer_url_title(url):
    import aiohttp

    async with aiohttp.ClientSession() as session:
        try:
            html = await fetch_html(session, url)
            title = await parse_page_title(html)
            return title
        except TimeoutError:
            return None


def sync_infer_url_title(url):
    from urllib.request import urlopen

    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(urlopen(url, timeout=2), "lxml")
        return soup.title.string
    except TimeoutError:
        return None
