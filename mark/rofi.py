import asyncio
import os
import shutil
from typing import List, Tuple


class Rofi:
    """
    A Rofi wrapper to abstract the subprocess calls
    """

    def __init__(
        self,
        limit: int = 10,
        prompt: str = "choose",
        matching: str = "fuzzy",
        fontname: str = "Monospace",
        fontsize: int = 21,
        sep: str = "\n",
        case_insensitive: bool = True,
        format: str = "i",  # returns the index of the selected item
        hover_select: bool = False,
    ):
        self.prompt = prompt
        self.limit = limit
        self.theme = "Monokai"
        self.fontname = fontname
        self.fontsize = fontsize
        self.matching = matching
        self.mode = "dmenu"
        self.sep = sep
        self.case_insensitive = case_insensitive
        self.format = format  # i means index
        self.hover_select = hover_select
        self.proc = None

    def check_rofi_installation(self):
        """Check if rofi is installed, if not raise Err"""
        path = shutil.which("rofi")
        if path is None:
            raise RuntimeError(
                "rofi is not installed, make sure to install it with your package manager"
            )

    async def __start_rofi_process(self, args: List) -> Tuple[str, int]:
        self.proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await self.proc.communicate()
        if self.proc.returncode == 0:
            quit()
        return stdout, self.proc.returncode

    def __get_common_args(self):
        assert self.matching in {"fuzzy", "normal", "regex", "glob", "prefix"}
        # fmt: off
        args = [
            "rofi",
            "-show", "mark",
            "-modes", "mark:./mark/script.py",
            "-sep", self.sep,
            "-matching", self.matching,
            "-theme", self.theme,
            "-font", f"{self.fontname} {self.fontsize}",
            "-format", self.format,
            "-p", self.prompt,
            "-l", str(self.limit),
        ]
        if self.case_insensitive:
            args.append("-i")
        if self.hover_select:
            args.append("-hover-select")
        return args

    def itemize(self, items: List) -> str:
        input_str = self.sep.join(items)
        return "".join(["dummy\n", input_str])

    def __prepare_data(
        self,
        args: List,
        items: List,
        pre_selected_idx: int = None,
        filter: str = "",
        msg: str = "",
    ):
        # process communication: send updated data to rofi
        os.environ["ROFI_INIT"] = self.itemize(items)
        if pre_selected_idx is not None:
            # +1 to accommodate the dummy line
            args.extend(["selected-row", str(pre_selected_idx + 1)])
        if filter:
            args.extend(["-filter", filter])
        if msg:
            args.extend(["-msg ", msg])
        return args

    def send_message(self, msg: str) -> bytes:
        line = f"\0message\x1f{msg}\n"
        return line.encode("utf8")

    def update_data(self, items: List = None, **kwargs) -> bytes:
        if not items:
            items = [" "]
        rofi_data = f"\0data\x1f{self.itemize(items)}\n"
        for option in kwargs:
            line = f"\0{option}\x1f{kwargs[option]}\n"
            rofi_data = "".join([rofi_data, line])
        return rofi_data.encode("utf8")

    async def open_menu(
        self,
        items: List,
        pre_selected_idx: int = None,
        filter: str = "",
        msg: str = "",
    ):
        self.check_rofi_installation()
        args = self.__get_common_args()
        args = self.__prepare_data(args, items, pre_selected_idx, filter, msg)
        await self.__start_rofi_process(args)
