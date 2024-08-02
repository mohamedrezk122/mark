import socket
import os


def concat(*args) -> str:
    return "".join(args)


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
PORT = int(os.environ["ROFI_PORT"])
client.connect(("localhost", PORT))
