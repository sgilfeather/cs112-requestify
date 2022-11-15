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

HOST = "127.0.0.1"  # loopback for working on cs112 server (TODO: customize)
PACK_SIZE = 1024
STATE = 0
    # STATE: -1 = quit / error, 0 = listening for new client
    #        1 = receiving from client, 2 = streaming to client
    #        3 = recieving from SoundCloud, 4 = requesting to SoundCloud   


class Server:
    def __init__(self, host_port):
        self.s_s = 0 # socket for listening for new clients

        # basic server functionality
        try: 
            self.s_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s_s.bind((HOST, host_port))
            self.s_s.listen()
        except Exception:
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
            print(f"We sent {num_sent} bytes!")
            return num_sent
        except Exception as e:
            print(f"Socket error: {str(e)}.\n")
            return -1; # client connection may have dropped out


    # run_server()
        # given a port, runs ( name ) server: writes file in PACK_SIZE
        # packets to client
    def run_server(self): 
        
        # TODO: outline program flow to order recv / write / req SoundCloud
        try:
            new_c_s, c_addr = self.s_s.accept() 
        except Exception as e:
            print(f"Socket error: {str(e)}.\n")
            return -1

        # TODO: for testing, read a file into buffer and write back
        with open("dog.jpg", "rb") as file:
            data = file.read(PACK_SIZE)
            result = 1

            while data and result > 0:
                result = self.write_frame(new_c_s, data)
                data = file.read(PACK_SIZE)
            
        new_c_s.close()
        return result # 0 if successful, -1 if an error occurred

#
# MAIN: get cmd-line arguments and run server
#
if len(sys.argv) != 2:
    print("Usage: python3 Server.py <server port>")
    quit()

host_port = sys.argv[1]
server = Server(int(host_port))
server.run_server()