#
# CLIENT.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Implementation of client in ( name ): connects to known ( name ) server,
# receives streamed audio data, and plays data through local machine audio
# output

import socket as socket

HOST = "127.0.0.1"  # loopback for working on cs112 server (TODO: customize)
PORT = 9050  # server's port
BUFF_SIZE = 1024

# basic client echo functionality

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c_s:
    c_s.connect((HOST, PORT))
    c_s.sendall(b"Hello, world!\n")

    data = c_s.recv(BUFF_SIZE)
    print(f"Received {data!s}")