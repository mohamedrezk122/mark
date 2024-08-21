import asyncio
import os
import shutil
from pathlib import Path
from typing import List, Tuple

from mark.utils import encode_message


class Rofi:
    """
    A Rofi wrapper to abstract the subprocess calls
    """

    def __init__(
        self,
        mode: str = "script",
        limit: int = 10,
        prompt: str = "mark",
        message: str = "",
        matching: str = "fuzzy",
        fontname: str = "Monospace",
        fontsize: int = 21,
        sep: str = "\n",
        case_insensitive: bool = True,
        format: str = "i",  # returns the index of the selected item
        hover_select: bool = False,
        paste_key: str = "Control+v",  # placeholder for now
    ):
        assert mode in ["dmenu", "script"]
        assert limit >= 1
        self.mode = mode
        self.limit = limit
        self.prompt = prompt
        self.message = message
        self.theme = "Monokai"
        self.fontname = fontname
        self.fontsize = fontsize
        self.matching = matching
        self.sep = sep
        self.case_insensitive = case_insensitive
        self.format = format  # i means index
        self.hover_select = hover_select
        self.paste_key = paste_key
        self.proc = None
        self.server_should_exit = False

    def setup_client(self, readwrite_mode, port):
        assert self.mode == "script"
        os.environ["ROFI_MODE"] = readwrite_mode
        os.environ["ROFI_PORT"] = str(port)
        return self

    def check_rofi_installation(self):
        """Check if rofi is installed, if not raise Err"""
        path = shutil.which("rofi")
        if path is None:
            raise RuntimeError(
                "rofi is not installed, make sure to install it with your"
                " package manager"
            )

    def kill_proc(self):
        try:
            self.proc.kill()
        except OSError:
            pass

    async def __start_rofi_process(
        self, args: List, sinput: List = None, timeout: int = 50
    ) -> Tuple:
        stdin = None
        if self.mode == "dmenu":
            stdin = asyncio.subprocess.PIPE
        self.proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=stdin,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                self.proc.communicate(input=sinput), timeout=timeout
            )
        except asyncio.exceptions.TimeoutError:
            try:
                self.proc.kill()
            except OSError:
                pass
            raise
        if self.proc.returncode == 0:
            self.server_should_exit = True
        return stdout, self.proc.returncode

    def __format_rofi_menu(self):
        # turn on markup for both prompt and message fields
        return [
            "-theme-str",
            """prompt {
                markup: true;
                font: "%s bold %s";
            }
            textbox {
                markup: true;
                horizontal-align: 0.5;
                text-outline: true;
            }
        """
            % (self.fontname, self.fontsize),
        ]

    def __get_common_args(self):
        assert self.matching in {"fuzzy", "normal", "regex", "glob", "prefix"}
        # fmt: off
        args = [
            "rofi",
            "-sep", self.sep,
            "-matching", self.matching,
            "-theme", self.theme,
            "-font", f"{self.fontname} {self.fontsize}",
            "-format", self.format,
            "-l", str(self.limit),
            "-show-icons",
        ]
        if self.mode == "script":
            script_file = (Path(__file__).parents[1]).joinpath("scripts/script.py")
            python_path = shutil.which("python3")
            args.extend([
                    "-show", "mark",
                    "-modes", f"mark:{python_path} {script_file}",
            ])
            if self.prompt:
                os.environ["ROFI_PROMPT"] = self.prompt
            if self.message:
                os.environ["ROFI_MESSAGE"] = self.message
        elif self.mode == "dmenu":
            args.extend(["-dmenu"])
            if self.prompt:
                args.extend(["-p", self.prompt])
        if self.case_insensitive:
            args.append("-i")
        if self.hover_select:
            args.append("-hover-select")
        return args

    def stringify(self, items: List, dummy: bool = True, meta: bool = False) -> str:
        if not meta:
            input_str = self.sep.join(items)
        else:  # for entries only not folders
            input_str = self.sep.join(
                [f"{title}\x00meta\x1f{url}" for title, url in items]
            )
        if not dummy:
            return input_str
        return "".join(["dummy\n", input_str])

    def __prepare_data(
        self,
        args: List,
        items: List,
        pre_selected_idx: int = None,
        filter: str = "",
    ):
        # process communication: send updated data to rofi
        if self.mode == "script":
            os.environ["ROFI_INIT"] = self.stringify(items)
        if pre_selected_idx is not None:
            # +1 to accommodate the dummy line
            args.extend(["selected-row", str(pre_selected_idx + 1)])
        if filter:
            args.extend(["-filter", filter])
        return args

    def send_message(self, msg: str) -> bytes:
        assert self.mode == "script"
        line = f"\x00message\x1f{msg}\n"
        return encode_message(line)

    def update_data(self, items: List = None, meta: bool = False, **kwargs) -> bytes:
        """
        if meta is True, the stringify function will look for the second index of
        each entry and add it after the `meta` key
        """
        assert self.mode == "script"
        rofi_data = "\x00data\x1f%s\n"
        if items is None:
            items = [" "]
        str_items = self.stringify(items, meta=meta)
        rofi_data = rofi_data % str_items
        for option in kwargs:
            line = f"\x00{option}\x1f{kwargs[option]}\n"
            rofi_data = "".join([rofi_data, line])
        return encode_message(rofi_data)

    async def open_menu(
        self,
        items: List,
        pre_selected_idx: int = None,
        filter: str = "",
    ):
        self.check_rofi_installation()
        args = self.__get_common_args()
        args.extend(self.__format_rofi_menu())
        args = self.__prepare_data(args, items, pre_selected_idx, filter)
        sinput = None
        if self.mode == "dmenu" and items:
            sinput = encode_message(self.stringify(items, dummy=False))
        await self.__start_rofi_process(args, sinput)


if __name__ == "__main__":
    # testing dmenu mode
    rofi = Rofi(mode="dmenu", prompt="Hi there")
    asyncio.run(rofi.open_menu(["hi", "hello", "welcome"]))
