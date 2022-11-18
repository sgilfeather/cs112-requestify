#
# SERVER.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Implementation of server in ( name ): connects, binds, and listens on a
# specified connection host for clients. Requests song data from SoundCloud
# using the SongFetcher module and streams data down to clients while
# listening for new clients

#!/usr/bin/python3

import sys
import socket as socket
import select
import sounddevice as sd
import numpy as np
import soundfile as sf
import time

HOST = "127.0.0.1"  # loopback for working on cs112 server (TODO: customize)
PACK_SIZE = 1024
STATE = 0
    # STATE: -1 = quit / error, 0 = listening for new client
    #        1 = receiving from client, 2 = streaming to client
    #        3 = recieving from SoundCloud, 4 = requesting to SoundCloud   


class Server:
    def __init__(self, host_port):
        self.s_s = 0 # socket for listening for new clients

        self.clients = [] # list of client sockets

        # basic server functionality
        try: 
            self.s_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s_s.bind((HOST, host_port))
            self.s_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s_s.listen()
        except Exception as e:
            print(f"Network error: {str(e)}.\n")
            sys.exit(0) 

        self.song_buff = b"\0"
        self.buff_len = -1
        self.buff_ind = 0 # index of current spot in song_buff

    def __del__(self):
        self.s_s.close()


    # write_frame()
        # writes a frame of data to client on socket c_s
    def write_frame(self, c_s, bytes):
        # get subarray from [buff_ind, buff_ind + PACK_SIZE)

        # write [buff_ind, buff_ind + PACK_SIZE) bytes to client
        try:
            num_sent = c_s.send(bytes)
            return num_sent
        except Exception:
            print(f"Client disconnected")
            return -1; # client connection may have dropped out


    # run_server()
        # given a port, runs ( name ) server: writes file in PACK_SIZE
        # packets to client
    def run_server(self): 
        
        # TODO: outline program flow to order recv / write / req SoundCloud

        bitrate = 44100
        send_delay = (PACK_SIZE / 8) / bitrate

        with open("songs/9851200.wav", "rb") as f:
            # Throw out header
            _ = f.read(44)
            # Read data
            data = f.read(PACK_SIZE)
            # Write data to client
            while data:
                for c_s in self.clients:
                    if self.write_frame(c_s, data) == -1:
                        self.clients.remove(c_s)
                # self.write_frame(new_c_s, data)
                data = f.read(PACK_SIZE)

                # Check for new clients with call to select()
                rlist, _, _ = select.select([self.s_s], [], [], 0)
                for s in rlist:
                    if s is self.s_s:
                        new_c_s, c_addr = self.s_s.accept()
                        self.clients.append(new_c_s)
                        print(f"New client connected: {c_addr}\n")
                
                time.sleep(send_delay)

        return 0

#
# MAIN: get cmd-line arguments and run server
#
if len(sys.argv) != 2:
    print("Usage: python3 Server.py <server port>")
    quit()

host_port = sys.argv[1]
server = Server(int(host_port))
server.run_server()