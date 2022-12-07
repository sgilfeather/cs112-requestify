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
from io import BufferedReader
import json

SELF = "127.0.0.1"  # loopback for hosting oneself

STATE = 0
    # STATE: -1 = quit / error, 0 = listening for new client
    #        1 = receiving from client, 2 = streaming to client
    #        3 = recieving from SoundCloud, 4 = requesting to SoundCloud   

SEED_FILE = "seeds.txt"
LOBBY_QUERY = "PokéCenter" 
CLOSE = "CLOSE_SERVER"


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
    open_file: BufferedReader   # current open song file

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
    host_s: socket.socket
    clients: list[socket.socket]
    channels: list[Channel]

    def __init__(self, host_port):
        self.host_s = 0
        self.clients = [] # list of client sockets
        self.channels = [] # list of channels
        self.client_map = {}    # maps client audio c_s's to comm c_s's

        # basic server functionality
        try: 
            self.host_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.host_s.bind((SELF, host_port))
            self.host_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.host_s.listen()
        except Exception as e:
            print(f"Network error: {str(e)}.\n")
            sys.exit(0) 


    def __del__(self):
        self.host_s.close()


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


    # write_song_packet()
    # constructs and writes a packet of audio data to client on socket c_s
    def write_song_packet(self, c_s, channel):
        # create a packet of data for this channel's current song
        data = channel.open_file.read(pack.AUDIO_PACK)

        while len(data) < pack.AUDIO_PACK:
            channel.next()
            data += channel.open_file.read(pack.AUDIO_PACK - len(data))

        try:
            num_sent = c_s.send(data)
            return num_sent
        except Exception:
            print(f"Client disconnected")
            return -1; # client connection may have dropped out


    # help_handle_cinit
    # handles C_INIT packet
    def help_handle_cinit(self, data, this_sock):
        # data[0] is "com" or "aud", data[1] is temp nonce
        # if nonce value is in map, finish the comm : audio mapping
        nonce = data[1]
        if nonce in self.client_map:
            # if comm socket connected first
            aud_sock = 0
            comm_sock = 0
            if self.client_map[nonce][0] == "com":
                comm_sock = self.client_map[nonce][1]
                # map comm sock to audio sock
                self.client_map[comm_sock] = this_sock
                aud_sock = this_sock

            elif self.client_map[nonce][0] == "aud":
                aud_sock = self.client_map[nonce][1]
                # map comm sock to audio sock
                self.client_map[this_sock] = aud_sock

            self.client_map.pop(nonce)
            # add client's audio socket to lobby channel
            self.channels[0].clients.append(aud_sock)
        else:
            # map nonce to first socket, and type of first socket
            self.client_map[nonce] = [data[0], this_sock]


    # handle_client_packet()
    # given a packet recieved from the client,
    def handle_client_packet(self, type, data, this_sock):
        if type== pack.C_INIT:
            self.help_handle_cinit(data, this_sock)


    # disconnect_client
    # removes a client from the given channel, and from the server
    # TODO: error checking on closing c_s?
    def disconnect_client(self, channel, c_s):
        # remove client if they disconnect
        print(f"Client disconnected")   # TODO: map client c_s to str name
        channel.clients.remove(c_s)
        self.clients.remove(c_s)
        c_s.close()


    # connect_new_client()
    # accept a new client, add them to the lobby channel, and send them the
    # initial setup packet (before writing any audio data to them)
    def connect_new_client(self):
        new_c_s, c_addr = self.host_s.accept()
        self.clients.append(new_c_s)    # add new client comm socket

        # write setup packet to client, containing list of channel names
        pack.write_packet(new_c_s, pack.S_INIT, [c.query for c in self.channels])


    # run_server()
    # given a port, runs ( name ) server: writes file in pack.AUDIO_PACK
    # packets to client
    def run_server(self, num_channels=4):
        bitrate = 44100
        send_delay = (pack.AUDIO_PACK / 8) / bitrate

        # Build list of playlists
        # Each playlist will be used for a channel
        # The first channel will be the lobby
        self.channels.append(Channel(LOBBY_QUERY, 1))
        self.channels.extend([Channel(seed, 2) for seed in get_seeds(num_channels)])

        self.print_channels()

        # TODO: while server doesn't recieve shutdown signal
        # from CLIENT on stdin
        while True:
            for channel in self.channels:
                
                for c_s in channel.clients:
                    # build and song packet to all clients on channel
                    if self.write_song_packet(c_s, channel) == -1:
                        self.disconnect_client(channel, c_s)
                        self.print_channels()

            # check for new clients and data from clients
            choices = [self.host_s] + [sys.stdin] + self.clients
            rlist, _, _ = select.select(choices, [], [], 0)

            for s in rlist:
                # Server socket is ready to accept a new client
                if s is self.host_s:
                    self.connect_new_client()
                    self.print_channels()
                # if CLOSE_SERVER is entered on command line, kill server
                elif s is sys.stdin:
                    str_in = sys.stdin.readline()[:-1]  # remove newline
                    if str_in == CLOSE:
                        return
                # else, Client socket sent data to be read
                else:
                    type, data = pack.read_packet(s)  # read packet from s
                    if type != -1:
                        self.handle_client_packet(type, data, s)
            
            time.sleep(pack.SEND_DELAY)


#
# MAIN: get cmd-line arguments and run server
#
if len(sys.argv) != 2:
    print("Usage: python3 Server.py <host port>")
    quit()

host_port = sys.argv[1]
server = Server(int(host_port))

server.run_server()
print("˖⁺｡˚⋆˙" * 10)
print("Thank you for running the Server.")