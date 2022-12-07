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
import socket as socket
import sounddevice as sd
from CircBuff import CircBuff
import Packet as pack 


#
# class Client
# client for the 
#
class Client:
    aud_s: socket.socket
    com_s: socket.socket
    song_buff: CircBuff
    curr_channel: int   # initialized to 0, lobby


    def __init__(self, host_addr, host_port):
        self.aud_s = -1 
        self.com_s = -1 
        self.curr_channel = 0
        self.chan_list = []

        # TODO: for now, just setting up audio stream
        try:
            self.aud_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.aud_s.connect((host_addr, host_port))
        except Exception as e:
            print(f"Client network error: {str(e)}.")
            sys.exit(0) 

        self.out_filename = "9851200.wav"
        # Remove the output file if it already exists
        if os.path.exists(self.out_filename):
            os.remove(self.out_filename)


    def __del__(self):
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


    # run_client()
    # executes loop for recieving streamed server data
    def run_client(self):
        stream = sd.RawOutputStream(
            samplerate=44100, blocksize=int(pack.AUDIO_PACK / 4),
            channels=2, dtype='int16',
            callback=self.stream_callback)

        # listen for init packets: first should contain lobby music,
        # second should contain channel options 
        print("˖⁺｡˚⋆˙" * 10)
        print(f"\nWelcome to the client!\n")
   

        with stream:
           # to exit, curr_channel is set to -1 (error state)
            while self.curr_channel > -1:
                time.sleep(1)


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