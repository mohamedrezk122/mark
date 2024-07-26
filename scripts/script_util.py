import socket
import os


def concat(str1: str, str2: str) -> str:
    return "".join([str1, str2])


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
PORT = int(os.environ["ROFI_PORT"])
client.connect(("localhost", PORT))
