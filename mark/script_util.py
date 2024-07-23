import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = 15555
client.connect(("localhost", port))
