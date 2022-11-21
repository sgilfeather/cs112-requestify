#
# CLIENT.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Implementation of client in ( name ): connects to known ( name ) server,
# and writes received data stream into a circular buffer
#

#!/usr/bin/python3

import os
import sys
import socket as socket
import time
import sounddevice as sd
import numpy as np

STATE = 0
PACK_SIZE = 1024
BUFF_SIZE = PACK_SIZE * 4

#
# class Client
# (description)
class Client:

    def __init__(self, host_addr, host_port):
        self.c_s = -1  # init in run_client()

        try:
            self.c_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"We set up the socket successfully\n")
            self.c_s.connect((host_addr, host_port))
        except Exception as e:
            print(f"Network error: {str(e)}.\n")
            sys.exit(0) 

        self.out_filename = "9851200.wav"
        # Remove the output file if it already exists
        if os.path.exists(self.out_filename):
            os.remove(self.out_filename)
        # TODO: make CircBuff field here after testing CircBuff

    def __del__(self):
        if isinstance(self.c_s, socket.socket):
            self.c_s.close()
    
    def stream_callback(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        new_data = self.read_frame()
        if len(new_data) == 0:
            raise sd.CallbackStop
        assert len(new_data) == len(outdata)
        outdata[:len(new_data)] = new_data
        outdata[len(new_data):] = b'\0' * (len(outdata) - len(new_data))

    # run_client()
    # executes loop for recieving streamed server data
    def run_client(self):
        result = 1
        stream = sd.RawOutputStream(
            samplerate=44100, blocksize=int(PACK_SIZE / 4),
            channels=2, dtype='int16',
            callback=self.stream_callback)

        with stream:
            while True:
                time.sleep(1)

        print("Client done")


        # while result > 0:
        #     result = self.read_frame()
        #     print(f"\n")

        return result # 0 if successful, -1 if an error occurred


    # read_frame()
        # reads a single frame from server on client's socket, c_s, and writes
        # it into client's circular buffer
    def read_frame(self):
        if not isinstance(self.c_s, socket.socket):
            print("Error: client socket not initialized")
            return b""
        
        try:
            print(f"About to recv from server\n")
            data = self.c_s.recv(PACK_SIZE) # make list
        except Exception as e:
            print(f"Read error: {str(e)}.\n")
            STATE = -1
            return b"" # client connection may have dropped out

        len_data = len(list(data))
        if len_data == 0: # no data recieved, return buffer of zeros
            return b"\0" * PACK_SIZE

        # calculate empty space left in circular buffer
        # space_left = self.circ_buff.sublen(self.buff_tail, self.buff_head)
        # if len_data > space_left:
        #     # overflow! for now, return -1
        #     print("Data overflow!\n")
        #     return -1
            
        # otherwise, append data to circular buffer
        # with open(self.out_filename, "ab") as f:
        #     result = f.write(data)
        #     print(f"Wrote {result} bytes to file")
        # self.circ_buff.append(data, len_data)

        return data
        # return np.frombuffer(data, dtype=np.int8).reshape(-1, 1)



#
# MAIN: get cmd-line arguments and run client
#
if len(sys.argv) != 3:
    print("Usage: python3 Client.py <server address> <server port>")
    quit()

host_addr = sys.argv[1]
host_port = sys.argv[2]

client = Client(host_addr, int(host_port))
client.run_client()