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
import socket as socket
import sounddevice as sd
from CircBuff import CircBuff
import Packet as pack 


#
# class Client
# client for the 
#
class Client:
    c_s: socket.socket
    song_buff: CircBuff
    curr_channel: int   # initialized to 0, lobby


    def __init__(self, host_addr, host_port):
        self.c_s = -1 
        self.song_buff = CircBuff(pack.BUFF_SIZE)
        self.curr_channel = 0
        self.chan_list = []

        try:
            self.c_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.c_s.connect((host_addr, host_port))
            self.c_s.setblocking(0)     # set to non-blocking
        except Exception as e:
            print(f"Client network error: {str(e)}.")
            sys.exit(0) 

        self.out_filename = "9851200.wav"
        # Remove the output file if it already exists
        if os.path.exists(self.out_filename):
            os.remove(self.out_filename)


    def __del__(self):
        if isinstance(self.c_s, socket.socket):
            self.c_s.close()
    

    def stream_callback(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        new_data = self.song_buff.consume(pack.PACK_SIZE)
        # buffer underflow, not enough song data; TODO send request
        if len(new_data) == 0:
            print("Song_buff is empty")
            raise sd.CallbackStop

        assert len(new_data) == len(outdata)
        outdata[:len(new_data)] = new_data
        outdata[len(new_data):] = b'\0' * (len(outdata) - len(new_data))


    # run_client()
    # executes loop for recieving streamed server data
    def run_client(self):
        stream = sd.RawOutputStream(
            samplerate=44100, blocksize=int(pack.PACK_SIZE / 4),
            channels=2, dtype='int16',
            callback=self.stream_callback)

        # listen for init packets: first should contain lobby music,
        # second should contain channel options 
        print("˖⁺｡˚⋆˙" * 10)
        print(f"\nWelcome to the client!\n")

        with stream:
           # to exit, curr_channel is set to -1 (error state)
            while self.curr_channel > -1:
                type, data = pack.read_packet(self.c_s)

                # for audio packet, type 1
                if type == 1:
                    # if we cannot append, song_buff is full
                    if not self.song_buff.append(list(data)):
                        print("Song_buff is full; skip ahead")
                        
                # for channel information packet, type 2
                elif type == 2:
                    # update list of channels
                    self.chan_list = data

                # if in lobby, offer channel selections
                if self.curr_channel == 0:
                    answ = 0 
                    while answ < 1 or answ > len(self.chan_list):
                        print("˖⁺｡˚⋆˙" * 5)
                        print(f"\nChoose a channel.")
                        for i in range(0, len(self.chan_list)):
                            print(f"{i + 1}) {self.chan_list[i]}")

                        try:
                            answ = int(input("... "))                          
                        except ValueError as ve:
                            answ = 0

                # else, if on a channel, offer request input
                else:
                    print("˖⁺｡˚⋆˙" * 5)
                    request = input(f"Make a vibe request (V), or choose a" +
                                     " new channel (C).\n")


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