#
# SERVER.PY
# (Soundcloud / Application name ) CS112, Fall 2022
# 
# Implementation of server in ( name ): connects, binds, and listens on a
# specified connection host for clients. Requests song data from SoundCloud
# using the SongFetcher module and streams data down to clients while
# listening for new clients
#

#!/usr/bin/python3

import sys
import os
import socket as socket
import select

import SongFetcher as sf
from SongFetcher import SONG_DIR
import Packet as pack 

import random
import time
import json

HOST = "127.0.0.1"  # loopback for working on cs112 server (TODO: customize)

STATE = 0
    # STATE: -1 = quit / error, 0 = listening for new client
    #        1 = receiving from client, 2 = streaming to client
    #        3 = recieving from SoundCloud, 4 = requesting to SoundCloud   

SEED_FILE = "seeds.txt"
LOBBY_QUERY = "PokéCenter" 


# get_seeds()
# parses seed file in project root directory, and returns the first
# num_seeds seeds extracted.
#
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


# class Channel
# records a list of current listening clients, and a queue of songs
# (filenames). maintains a non-empty playlist of songs; on next(), the 
# next song is opened as BufferedReader open_file
#
class Channel:
    songs: list     # maintained list of songs
    query: str      # current query to SoundCloud 
    clients: list   # current clients, identified by socket fd 

    def __init__(self, query, num_songs=1):
        self.songs = []
        self.query = query
        self.clients = []
        print(f"new channel: {query}")
        
        self.fill(num_songs)

        next_song = self.songs.pop(0)
        self.open_file = open(os.path.join(SONG_DIR, next_song), "rb")
        # throw out wav header
        _ = self.open_file.read(44)
    
    def __del__(self):
        if self.open_file:
            self.open_file.close()

    # fill()
    # for each song retrieved from SongFetcher query, download its audio
    # byte data and append it to songs list 
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


# class Server
#
#
class Server:
    s_s: socket.socket
    clients: list[socket.socket]
    channels: list[Channel]

    def __init__(self, host_port):
        self.clients = [] # list of client sockets
        self.channels = [] # list of channels

        # basic server functionality
        try: 
            self.s_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s_s.bind((HOST, host_port))
            self.s_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s_s.listen()
        except Exception as e:
            print(f"Network error: {str(e)}.\n")
            sys.exit(0) 


    def __del__(self):
        self.s_s.close()


    # swap_client_channel()
    # moves client from old channel, old_ch, to new channel, new_ch
    def swap_client_channel(self, client, old_ch: Channel, new_ch: Channel):
        old_ch.clients.remove(client)
        new_ch.clients.append(client)
        print(f"Client {client} moved from channel {old_ch.query} to \
                channel {new_ch.query}")


    # print_channels()
    # prints diagnostic information about each client on each channel
    def print_channels(self):
        for channel in self.channels:
            print(f"Channel {channel.query}: {len(channel.clients)} clients")
        print("-" * 20)


    # run_server()
        # given a port, runs ( name ) server: writes file in pack.PACK_SIZE
        # packets to client
        # TEST: file that's just over pack.PACK_SIZE big
    def run_server(self, num_channels=2):
        bitrate = 44100
        send_delay = pack.DATA_SIZE / bitrate / 8

        # Build list of playlists
        # Each playlist will be used for a channel
        # The first channel will be the lobby
        self.channels.append(Channel(LOBBY_QUERY, 1))
        self.channels.extend([Channel(seed, 2) for seed in get_seeds(num_channels)])

        self.print_channels()

        # TODO: while server doesn't recieve shutdown signal
        while True:
            for channel in self.channels:

                # write a packet of data for this channel's current song
                data = channel.open_file.read(pack.DATA_SIZE)

                while len(data) < pack.DATA_SIZE:
                    channel.next()
                    data += channel.open_file.read(pack.DATA_SIZE - len(data))

                for c_s in channel.clients:
                    # Send song packet to all clients on channel
                    if not pack.write_packet(c_s, 1, data):
                        # and remove client if they disconnect
                        print(f"Client disconnected")
                        channel.clients.remove(c_s)
                        self.clients.remove(c_s)
                        c_s.close()
                        self.print_channels()

            # check for new clients and data from clients
            rlist, _, _ = select.select([self.s_s] + self.clients, [], [], 0)

            for s in rlist:
                # Server socket is ready to accept a new client
                if s is self.s_s:
                    new_c_s, c_addr = self.s_s.accept()
                    # add new client to the lobby channel
                    self.channels[0].clients.append(new_c_s)
                    self.clients.append(new_c_s)
                    self.print_channels()
                    chan_list = ",".join([channel.query for channel in self.channels])
                    pack.write_packet(new_c_s, 2, chan_list)

                # Client socket sent data to be read
                else:
                    try:
                        packet = s.recv(pack.PACK_SIZE)
                        if packet:
                            print(f"Recieved {str(packet)}.")
                    except:
                        continue
                    # data = json.loads(packet)["d"]
                    # print(f"Received {data} from client")
            
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