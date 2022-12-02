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
import os
import socket as socket
import select
import time
from typing import Optional
import SongFetcher as sf
from SongFetcher import SONG_DIR
import random
from io import BufferedReader

HOST = "127.0.0.1"  # loopback for working on cs112 server (TODO: customize)
PACK_SIZE = 1024
STATE = 0
    # STATE: -1 = quit / error, 0 = listening for new client
    #        1 = receiving from client, 2 = streaming to client
    #        3 = recieving from SoundCloud, 4 = requesting to SoundCloud   

SEED_FILE = "seeds.txt"

def get_seeds(num_seeds):
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r") as f:
            seeds = f.read().splitlines()
            while len(seeds) < num_seeds:
                seeds += seeds
            random.shuffle(seeds)
            return seeds[:num_seeds]
    else:
        raise Exception(f"Couldn't find {SEED_FILE} in current directory")

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

    class Channel:
        songs: list
        query: str
        clients: list
        open_file: BufferedReader

        def __init__(self, query):
            self.songs = []
            self.query = query
            self.clients = []
            self.fill()
            next_song = self.songs.pop(0)
            self.open_file = open(os.path.join(SONG_DIR, next_song), "rb")
            # Throw out wav header
            _ = self.open_file.read(44)
        
        def __del__(self):
            if self.open_file:
                self.open_file.close()

        def fill(self, num_songs=1):
            search_results = sf.search(self.query, num_songs)
            for result in search_results:
                self.songs.append(sf.download_song(result))
        
        def next(self):
            if self.open_file:
                self.open_file.close()
            if len(self.songs) == 0:
                self.fill()
            next_song = self.songs.pop(0)
            self.open_file = open(os.path.join(SONG_DIR, next_song), "rb")
            # Throw out wav header
            _ = self.open_file.read(44)

    def swap_client_channel(self, client, old_channel: Channel, new_channel: Channel):
        old_channel.clients.remove(client)
        new_channel.clients.append(client)
        print(f"Client {client} moved from channel {old_channel.query} to channel {new_channel.query}")

    # run_server()
        # given a port, runs ( name ) server: writes file in PACK_SIZE
        # packets to client
        # TEST: file that's just over PACK_SIZE big
    def run_server(self, channels=4):
        
        # TODO: outline program flow to order recv / write / req SoundCloud

        bitrate = 44100
        send_delay = (PACK_SIZE / 8) / bitrate

        # Build list of playlists
        # Each playlist will be used for a channel
        seeds = get_seeds(channels)
        channels = [self.Channel(seed) for seed in seeds]

        while True:
            for channel in channels:
                print(f"Channel {channel.query} has {len(channel.clients)} clients")
                data = channel.open_file.read(PACK_SIZE)
                while len(data) < PACK_SIZE:
                    channel.next()
                    data += channel.open_file.read(PACK_SIZE - len(data))
                for c_s in channel.clients:
                    # Send song data to client...
                    if self.write_frame(c_s, data) == -1:
                        # and remove client if they disconnect
                        channel.clients.remove(c_s)
            print("-" * 20)
            # Check for new clients with call to select()
            rlist, _, _ = select.select([self.s_s], [], [], 0)
            for s in rlist:
                if s is self.s_s:
                    new_c_s, c_addr = self.s_s.accept()
                    # TODO: add client to channel of their choice, or a sentinel until they send a JOIN
                    rand_channel = random.randrange(0, len(channels))
                    channels[rand_channel].clients.append(new_c_s)
                    print(f"New client connected: {c_addr}. Added to channel {rand_channel} with query {channels[rand_channel].query}")
            
            time.sleep(send_delay)

#
# MAIN: get cmd-line arguments and run server
#
if len(sys.argv) != 2:
    print("Usage: python3 Server.py <server port>")
    quit()

host_port = sys.argv[1]
server = Server(int(host_port))
server.run_server()