#
# CLIENT.PY
# (Soundcloud / Application name ) CS112, Fall 2022
# 
# Implementation of client in ( name ): connects to known ( name ) server,
# and writes received data stream into a circular buffer
#

#!/usr/bin/python3

import os
import sys
import json
import time
import string
import random

import select
import socket as socket
import sounddevice as sd
import Packet as pack 


SELF = "127.0.0.1"  # loopback for hosting oneself
NONCE_VALS = string.ascii_uppercase + string.ascii_lowercase + string.digits

#
# class Client
# client for the 
#
class Client:
    aud_s: socket.socket
    com_s: socket.socket
    nonce: string
    curr_channel: int   # initialized to 0, lobby


    def __init__(self, host_addr, host_port):
        self.aud_s = -1     # receives audio data
        self.com_s = -1     # writes and reads messages to / from server
        self.nonce = ''.join(random.choices(''.join(NONCE_VALS), k=4))
        
        self.host_addr = host_addr
        self.host_port = host_port

        self.curr_channel = 0
        self.chan_list = []

        # TODO: for now, just setting up audio streams
        try:
            self.com_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.com_s.connect((host_addr, host_port))
        except Exception as e:
            print(f"Client network error for audio sock: {str(e)}.")
            sys.exit(0) 

        self.out_filename = "9851200.wav"
        # Remove the output file if it already exists
        if os.path.exists(self.out_filename):
            os.remove(self.out_filename)


    def __del__(self):
        if isinstance(self.com_s, socket.socket):
            self.com_s.close()

        if isinstance(self.aud_s, socket.socket):
            self.aud_s.close()
    

    def stream_callback(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        new_data = self.read_frame()

        if len(new_data) == 0:
            raise sd.CallbackStop
        outdata[:len(new_data)] = new_data
        outdata[len(new_data):] = b'\0' * (len(outdata) - len(new_data))


    # send_init_packet()
    # set up client's channel list, and set up a separate communications
    # port for the c_s
    def send_init_packet(self, data):
        # data should be the list ["channel_1", ... "channel_len"]
        self.chan_list = data
        # associate both aud_s and com_s on serverside with given nonce
        pack.write_packet(self.com_s, pack.C_INIT, ["com", self.nonce])

        # setup new port for communications
        try:
            self.aud_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.aud_s.connect((self.host_addr, self.host_port))
        except Exception as e:
            print(f"Client network error for com sock: {str(e)}.")
            sys.exit(0) 

        pack.write_packet(self.aud_s, pack.C_INIT, ["aud", self.nonce])

    def print_menu(self):
        print("˖⁺｡˚⋆˙" * 10)
        print("\tjoin <channel>")
        print("\tlist")
        print("\texit")
        print("Choose an option:")
    
    def join_channel(self, query):
        pack.write_packet(self.com_s, pack.C_JOIN, query)   # TODO: if returns -1

    def print_channels(self):
        pack.write_packet(self.com_s, pack.C_LIST, "")


    def client_handle_packet(self, type, data):
        if type == pack.S_INIT:
            self.chan_list = data
        elif type == pack.S_LIST:
            print("˖⁺｡˚⋆˙" * 10)
            print("Channels:")
            for i in range(len(data)):
                print(f"\t{data[i]}")


    # run_client()
    # executes loop for recieving streamed server data
    def run_client(self):
        stream = sd.RawOutputStream(
            samplerate=44100, blocksize=int(pack.AUDIO_PACK / 4),
            channels=2, dtype='int16',
            callback=self.stream_callback)

        print("˖⁺｡˚⋆˙" * 10)
        print(f"\nWelcome to the client!\n")
        self.print_menu()
   
        # listen for init packets: first packet on com_s stream should
        # contain setup com port with channel options
        type, data = pack.read_packet(self.com_s)
        if type != pack.S_INIT:
            print(f"Error: did not recieve init packet from server.")
            return
        
        self.send_init_packet(data) 

        with stream:
           # to exit, curr_channel is set to -1 (error state)
            while self.curr_channel > -1:
                # check for input messages
                
                rlist, _, _ = select.select([sys.stdin, self.com_s], [], [], 0)
                for s in rlist:
                    if sys.stdin in rlist:
                        line = sys.stdin.readline()
                        line = line.strip()
                        if line.startswith("join "):
                            self.join_channel(line[5:])
                        elif line == "list":
                            self.print_channels()
                        elif line == "quit" or line == "exit":
                            self.curr_channel = -1
                        else:
                            print("Invalid option")
                        self.print_menu()
                    else:
                        # TODO: remove MSG writing
                        # pack.write_packet(s, pack.C_MSG, "Hello server!")
                        type, data = pack.read_packet(s)  # read packet from s
                        if type != -1:
                            self.client_handle_packet(type, data)

    # read_frame()
        # reads a single audio frame from the server's audio socket to the
        # client's audio socket, returning the byte data read
    def read_frame(self):
        if not isinstance(self.aud_s, socket.socket):
            print("Error: client socket not initialized")
            return b""
        
        try:
            data = self.aud_s.recv(pack.AUDIO_PACK) # make list
        except Exception as e:
            print(f"Read error: {str(e)}.\n")
            STATE = -1
            return b"" # client connection may have dropped out

        len_data = len(list(data))
        if len_data == 0: # no data recieved, return buffer of zeros
            return b"\0" * pack.AUDIO_PACK
        
        return data

#
# MAIN: get cmd-line arguments and run client
#
if len(sys.argv) != 3:
    print(f"Usage: python {sys.argv[0]} <server address> <server port>")
    exit(1)

host_addr = sys.argv[1]
host_port = sys.argv[2]

client = Client(host_addr, int(host_port))
client.run_client()