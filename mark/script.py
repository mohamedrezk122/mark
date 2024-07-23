#!/usr/bin/env python3
"""
    This file is a rofi script, see: 
        https://davatorium.github.io/rofi/1.7.3/rofi-script.5
    Also, it behaves as a client for the rofi wrapper.
    WARNING: print statements are not for debugging, they are used to redirect 
        output to rofi input stream
"""
import json
import os
import sys

from mark.script_util import client

# initially list the items from ROFI_INIT env variable
# after the first selection, selected item is written to ROFI_DATA env variable
if os.getenv("ROFI_INIT") is not None and os.getenv("ROFI_DATA") is None:
    no_custom = ""
    # don't allow custom inputs in read mode, only choose from listed items
    if os.environ["ROFI_MODE"] == "read":
        no_custom = "\0no-custom\x1ftrue\n"
    data = "\0data\x1f%s\n%s" % (os.environ["ROFI_INIT"], no_custom)
    del os.environ["ROFI_INIT"]
    # send initial list to rofi
    print(data)

# there is an item selected
if len(sys.argv) > 1:
    msg = json.dumps(
        {
            # 1: item selected from the list
            # 2: custom item selected
            "code": int(os.environ["ROFI_RETV"]),
            # selected item
            "value": sys.argv[1],
        }
    )
    client.send(msg.encode("utf8"))
    data = client.recv(500).decode("utf8")
    if data == "quit":
        client.close()
    else:
        # send updated data to rofi
        print(data)
