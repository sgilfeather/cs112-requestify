#
# SERVER.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Implementation of server in ( name ): connects, binds, and listens on a
# specified connection host for clients. Requests song data from SoundCloud
# using the SongFetcher module and streams data down to clients while
# listening for new clients

import socket as socket

HOST = "127.0.0.1"  # loopback for working on cs112 server (TODO: customize)
PORT = 9050  # server's port
BUFF_SIZE = 1024

# basic server echo functionality
    # state: 0 = listening for new client
    #        1 = listening to client, 2 = streaming to client
    #        3 = listening to SoundCloud, 4 = writing to SoundCloud   

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_s:
    state = 0
    data = [0] * BUFF_SIZE

    s_s.bind((HOST, PORT))
    s_s.listen()
    new_c_s, c_addr = s_s.accept() # new client socket and client's address 

    with new_c_s: # write to client
        state = 1
        while state != 0:
            data = new_c_s.recv(BUFF_SIZE) # could block

            if data:
                print(f"Received {data!s}")
                new_c_s.sendall(b"Hello back!\n") 
            else:
                state = 0 # client closed, search for another client
            