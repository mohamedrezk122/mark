import asyncio
import json
import os
import platform
import subprocess
from typing import Callable

from mark.db import DataBase
from mark.rofi import Rofi


class Server:
    def __init__(
        self, db_filename: str, mode: str = "read", on_selection: Callable | None = None
    ):
        assert mode in ["read", "write"], "mode has to be 'read' or 'write'"
        prompt = "choose dir"
        self.mode = mode
        self.db = DataBase(db_filename)
        os.environ["ROFI_MODE"] = self.mode
        self.rofi = Rofi(prompt=prompt)
        self.on_selection = on_selection
        self.parent_path = None  # selected parent dir
        # container for bookmark insertion
        self.pack = {"current": 0}

    async def __close_connection(self, writer: asyncio.StreamWriter):
        writer.write("quit".encode("utf8"))
        await writer.drain()

    async def __handle_root_selection(self, writer: asyncio.StreamWriter, root: str):
        # TODO: be presistant ?
        title, url = self.db.get_bookmark(self.parent_path, root)
        self.on_selection(title, url)
        await self.__close_connection(writer)

    async def __handle_path_selection(self, writer: asyncio.StreamWriter, path: str):
        # TODO: handle hierarchical paths
        self.parent_path = path
        items = self.db.list_bookmarks(path)
        kwargs = {
            "prompt": "choose bookmark",
        }
        data = self.rofi.update_data(items, **kwargs)
        writer.write(data)
        await writer.drain()

    async def __handle_insertion_message(
        self, writer: asyncio.StreamWriter, type_: str, value: str
    ):
        # TODO: handle hierarchical paths
        assert type_ in ["path", "url", "title"]
        self.pack[type_] = value
        if type_ == "title":
            return
        kwargs = {
            "prompt": "insert url or location",
            # TODO: paste key
            "message": "Paste with key",
        }
        if type_ == "url":
            kwargs["prompt"] = "insert title"
        data = self.rofi.update_data(None, **kwargs)
        writer.write(data)
        await writer.drain()

    async def __handle_bookmark_insertion(
        self, writer: asyncio.StreamWriter, value: str
    ):
        # iterate over these modes in this order
        types = ["path", "url", "title"]
        type_ = types[self.pack["current"]]
        await self.__handle_insertion_message(writer, type_, value)
        self.pack["current"] += 1
        if self.pack["current"] > 2:
            self.db.insert_bookmark(
                self.pack["path"], self.pack["title"], self.pack["url"]
            )
            await self.__close_connection(writer)

    async def __handle_readwrite_mode(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        while True:
            response = (await reader.read(500)).decode("utf8")
            # response format -> {"code": return_code, "value": selected_item}
            if response is None:
                continue
            response = json.loads(response)
            if self.mode == "read" and not self.db.is_dir(response["value"]):
                await self.__handle_root_selection(writer, response["value"])
            elif self.mode == "read":
                await self.__handle_path_selection(writer, response["value"])
            elif self.mode == "write":
                await self.__handle_bookmark_insertion(writer, response["value"])
        writer.close()
        await writer.wait_closed()

    async def run_server(self):
        server = await asyncio.start_server(
            self.__handle_readwrite_mode, host="localhost", port=15555
        )
        async with server:
            await server.serve_forever()


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
        subprocess.run(["open", url])
        return
    # Linux or BSD
    try:
        subprocess.run(["xdg-open", url])
    except OSError:
        raise RuntimeError("Cannot open default browser")
