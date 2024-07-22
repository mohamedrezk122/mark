import asyncio
import json
import os
import platform
import subprocess
from typing import Callable

from mark.db import DataBase
from mark.rofi import Rofi


class Server:
    def __init__(self, db_filename, mode, on_selection: Callable = None):
        assert mode in ["read", "write"], "mode has to be 'read' or 'write'"
        prompt = "Choose Dir"
        self.mode = mode
        self.db = DataBase(db_filename)
        os.environ["ROFI_MODE"] = "write"
        if self.mode == "read":
            os.environ["ROFI_MODE"] = "read"
        self.rofi = Rofi(prompt=prompt)
        self.on_selection = on_selection
        self.parent_path = None  # selected parent dir

    async def __handle_read_mode(self, reader, writer):
        while True:
            response = (await reader.read(500)).decode("utf8")
            # response -> {"code": return_code, "value": selected_item}
            if response is None:
                continue
            response = json.loads(response)
            # selected item is listed
            if response["code"] != 1:
                continue 
            if not self.db.is_dir(response["value"]):
                # TODO: be presistant ?
                name, url = self.db.get_bookmark(
                    self.parent_path, response["value"]
                )
                self.on_selection(name, url)
                writer.write("quit".encode("utf8"))
                await writer.drain()
                break
            self.parent_path = response["value"]
            items = self.db.list_bookmarks(response["value"])
            kwargs = {
                "prompt": "Choose bookmark",
            }
            data = self.rofi.update_data(items, **kwargs)
            writer.write(data)
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def __handle_write_mode(self, reader, writer):
        # TODO: implement bookmark insertion function
        raise NotImplementedError()

    async def run_server(self):
        handler = self.__handle_write_mode
        if self.mode == "read":
            handler = self.__handle_read_mode
        server = await asyncio.start_server(handler, host="localhost", port=15555)
        async with server:
            await server.serve_forever()


def copy_selection(name, url):
    import pyperclip

    pyperclip.copy(url)


def open_selection(name, url):
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
        print("Cannot open default browser")


async def main():
    async_server = Server("db.yaml", mode="read", on_selection=open_selection)
    await asyncio.gather(
        async_server.rofi.open_menu(async_server.db.list_dirs()),
        async_server.run_server(),
    )


asyncio.run(main())
