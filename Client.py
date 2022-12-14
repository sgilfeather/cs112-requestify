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
MSG_MAX = 140

#
# class Client
# client for the 
#
class Client:
    aud_s: socket.socket
    com_s: socket.socket
    nonce: str
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


    # print_menu()
    # prints menu with client's current list of channels
    def print_menu(self):
        print("\n" + "˖⁺｡˚⋆˙" * 10)
        print("Options:")
        print("\tjoin [ channel ]")
        print("\tlist")
        print("\trequest [ query ]")
        print("\tchat [ message ]")
    
    # join_channel()
    # wrapper to send C_JOIN packet to Server to join new channel
    def join_channel(self, query):
        pack.write_packet(self.com_s, pack.C_JOIN, query)
        # TODO: update internal "curr_channel"

    # request_channels
    # wrapper to send C_LIST packet and ask Server for updated channel list
    def request_channels(self):
        pack.write_packet(self.com_s, pack.C_LIST, "")

    # request_song
    # wrapper to send C_REQ packet and ask Server to add a song from query
    def request_song(self, query):
        pack.write_packet(self.com_s, pack.C_REQ, query)

    # write_chat()
    # writes a chat of maximum MSG_MAX characters to all other clients on
    # this client's channel
    def write_chat(self, message):
        if len(message) > MSG_MAX:
            print(f"Error: message \"{message[:20]}...\" too long.\n")
            return
        pack.write_packet(self.com_s, pack.C_MSG, message)


    # client_handle_packet()
    # helper func to process packets recived from the Server
    def client_handle_packet(self, type, data):
        # initial 'hello' packet, and set channel list
        if type == pack.S_INIT:
            self.chan_list = data

        # print list of channels
        elif type == pack.S_LIST:
            self.chan_list = data   # update channel list
            print("˖⁺｡˚⋆˙" * 10)
            print("Channels:")
            for i in range(len(data)):
                print(f"\t{data[i]}")

        elif type == pack.S_MSG:
            print(f"<user>: {data}\n")

    # client_handle_user_input()
    # reads a single line from user and parses it for command input
    # commands are case-insensitive– if a command is invalid, 
    def client_handle_user_input(self):
        line = sys.stdin.readline()
        line = line.strip().lower()     # input is case insensitive

        if line.startswith("join "):
            self.join_channel(line[5:])
        elif line == "list":
            self.request_channels()
        elif line.startswith("request "):
            self.request_song(line[8:])
        elif line == "quit" or line == "exit":
            self.curr_channel = -1
        elif line.startswith("chat "):
            self.write_chat(line[5:])
        elif line == "help":
            self.print_menu()
        else:
            print("Invalid option.")
        

    # run_client()
    # executes loop for recieving streamed server data
    def run_client(self):
        stream = sd.RawOutputStream(
            samplerate=44100, blocksize=int(pack.AUDIO_PACK / 4),
            channels=2, dtype='int16',
            callback=self.stream_callback)
   
        # listen for init packets: first packet on com_s stream should
        # contain setup com port with channel options
        type, data = pack.read_packet(self.com_s)
        if type != pack.S_INIT:
            print(f"Error: did not recieve init packet from server.")
            return
        
        self.send_init_packet(data) 

        print("˖⁺｡˚⋆˙" * 10)
        print(f"\nWelcome to the client!")
        self.print_menu()
        print("Choose an option: \n* ", end="")

        with stream:
           # to exit, curr_channel is set to -1 (error state)
            while self.curr_channel > -1:

                rlist, _, _ = select.select([sys.stdin, self.com_s], [], [], 0)
                # check for new messages on comm socket, or input from user
                for s in rlist:
                    # read a communications packet from Server 
                    if s == self.com_s:
                        print("")
                        type, data = pack.read_packet(s)
                        self.client_handle_packet(type, data)
                        print("\n* ", end="", flush=True)
                        
                    # if input from the user, parse and handle input!
                    elif s == sys.stdin:
                        self.client_handle_user_input();
                        print("\n* ", end="", flush=True)
                    

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