import asyncio
import json

from tinydb import TinyDB

from mark.rofi import Rofi
from mark.utils import copy_selection, open_selection


class Server:
    def __init__(
        self,
        port: int,
        db: TinyDB,
        mode: str = "read",
        rofi_inst: Rofi = None,
        on_selection: str = None,
    ):
        assert mode in ["read", "write"], "mode has to be 'read' or 'write'"
        self.mode = mode
        self.port = port
        self.rofi = rofi_inst
        self.db = db
        self.on_selection = on_selection
        # container for selection tracking
        self.pack = {"current": 0}

    async def __close_connection(self, writer: asyncio.StreamWriter):
        writer.write("quit".encode("utf8"))
        await writer.drain()

    async def __handle_root_selection(self, writer: asyncio.StreamWriter, root: str):
        on_selection_funcs = {
            "copy": copy_selection,
            "open": open_selection,
        }
        title, url = self.db.get_bookmark(self.pack["path"], root)
        on_selection_funcs[self.on_selection](title, url)
        await self.__close_connection(writer)

    async def __handle_path_selection(self, writer: asyncio.StreamWriter, path: str):
        # TODO: handle hierarchical paths
        self.pack["path"] = path
        items = self.db.list_bookmarks(path)
        kwargs = {
            "message": "choose bookmark",
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
        state = "url"
        if type_ == "url":
            state = "title"
        kwargs = {
            # TODO: paste key
            "message": f"insert {state} (paste with key {self.rofi.paste_key})",
        }
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
            if self.rofi.server_should_exit:
                quit()
            try:
                await asyncio.sleep(0)
                response = await reader.read(500)
                # response format -> {"code": return_code, "value": selected_item}
                if response is None:
                    continue
                response = json.loads(response.decode("utf8"))
                res_value = response["value"]
                if self.mode == "read" and not self.db.is_dir(res_value):
                    await self.__handle_root_selection(writer, res_value)
                elif self.mode == "read":
                    await self.__handle_path_selection(writer, res_value)
                elif self.mode == "write":
                    await self.__handle_bookmark_insertion(writer, res_value)
            except:
                continue
        writer.close()
        await writer.wait_closed()

    async def run_server(self):
        server = await asyncio.start_server(
            self.__handle_readwrite_mode, host="localhost", port=self.port
        )
        async with server:
            await server.serve_forever()
