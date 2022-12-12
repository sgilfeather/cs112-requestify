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
SONG_LIST_SIZE = 2


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

    def __init__(self, query, num_songs=SONG_LIST_SIZE):
        self.songs = []
        self.query = query
        self.clients = []
        self.open_file = None
        print(f"new channel: {query}")
        
        self.fill(SONG_LIST_SIZE)

        if len(self.songs) > 0:
            next_song = self.songs[0]
            self.open_file = open(os.path.join(SONG_DIR, next_song), "rb")
            # throw out wav header
            _ = self.open_file.read(44)
    
    def __del__(self):
        if self.open_file:
            self.open_file.close()


    # fill()
    # for each song retrieved from SongFetcher query, download its audio
    # byte data and append it to songs list 
    def fill(self, num_songs=SONG_LIST_SIZE):
        search_results = sf.search(self.query, num_songs)
        for result in search_results:
            song = sf.download_song(result)
            if song is None:
                continue
            self.songs.append(song)
    

    def next(self):
        if self.open_file:
            self.open_file.close()
        
        if len(self.songs) == 0:
            self.fill()

        # Rotate song list
        self.songs = self.songs[1:] + self.songs[:1]

        next_song = self.songs[0]
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
        self.client_map = {}    # maps client audio c_s's to com c_s's

        print("About to open the server socket.")
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


    # move_client()
    # moves client from their current channel to new channel, new_ch
    def move_client(self, client, new_ch: Channel):
        for channel in self.channels:
            if client in channel.clients:
                channel.clients.remove(client)
        new_ch.clients.append(client)
        
        print(f"Client moved to channel {new_ch.query}")
        self.print_channels()


    # print_channels()
    # prints diagnostic information about each client on each channel
    def print_channels(self):
        for channel in self.channels:
            # TODO: not printing out length of channel?
            print(f"Channel {channel.query}: {len(channel.clients)} clients")
        print("-" * 20)


    # write_song_packets()
    # constructs and writes a packet of audio data to each client in the channel
    def write_song_packets(self, channel):
        # create a packet of data for this channel's current song
        data = channel.open_file.read(pack.AUDIO_PACK)

        while len(data) < pack.AUDIO_PACK:
            channel.next()
            data += channel.open_file.read(pack.AUDIO_PACK - len(data))
        
        # write packet to each client on this channel
        for (c_com, c_aud) in channel.clients:
            try:
                num_sent = c_aud.send(data)
                return num_sent
            except Exception:
                print(f"Client disconnected")
                self.disconnect_client(channel, c_com)
                self.print_channels()
                


    # help_handle_cinit
    # handles C_INIT packet
    def help_handle_cinit(self, data, this_sock):
        # data[0] is "com" or "aud", data[1] is temp nonce
        # if nonce value is in map, finish the com : audio mapping
        nonce = data[1]
        if nonce in self.client_map:
            # if com socket connected first
            aud_sock = 0
            com_sock = 0
            if self.client_map[nonce][0] == "com":
                com_sock = self.client_map[nonce][1]
                # map com sock to audio sock
                self.client_map[com_sock] = this_sock
                aud_sock = this_sock

            elif self.client_map[nonce][0] == "aud":
                aud_sock = self.client_map[nonce][1]
                # map com sock to audio sock
                self.client_map[this_sock] = aud_sock

            self.client_map.pop(nonce)
            # add client's audio socket to lobby channel
            self.channels[0].clients.append((com_sock, aud_sock))
        else:
            # map nonce to first socket, and type of first socket
            self.client_map[nonce] = [data[0], this_sock]

        self.print_channels()

    # server_handle_packet()
    # given a packet recieved from the client,
    def server_handle_packet(self, type, data, c_com):
        if type == pack.C_INIT:
            self.help_handle_cinit(data, c_com)
        # elif type == pack.C_MSG:
        #     print(f"Recieved from client: {data}")
        elif type == pack.C_JOIN:
            c_aud = self.client_map[c_com]
            for channel in self.channels:
                if channel.query == data:
                    self.move_client((c_com, c_aud), channel)
                    break
        elif type == pack.C_LIST:
            # send list of channels to client
            pack.write_packet(c_com, pack.S_LIST, [channel.query for channel in self.channels])
        elif type == pack.C_REQ:
            # No request query given
            if len(data) == 0:
                return
            c_aud = self.client_map[c_com]
            for channel in self.channels:
                if (c_com, c_aud) in channel.clients:
                    channel.query = data
                    channel.songs = []
                    channel.next()
                    break
            pack.write_packet(c_com, pack.S_LIST, [channel.query for channel in self.channels])
            self.print_channels()


    # disconnect_client
    # removes a client from the given channel, and from the server
    # TODO: error checking on closing c_s?
    def disconnect_client(self, channel, c_com):
        # Try to find socket in client_map
        c_aud = self.client_map[c_com]
        channel.clients.remove((c_com, c_aud))
        self.clients.remove(c_com)
        self.clients.remove(c_aud)
        self.client_map.pop(c_com)
        c_com.close()
        c_aud.close()
        # remove client if they disconnect
        print(f"Client disconnected")


    # connect_new_client()
    # accept a new client, add them to the lobby channel, and send them the
    # initial setup packet (before writing any audio data to them)
    def connect_new_client(self):
        new_c_s, c_addr = self.host_s.accept()
        self.clients.append(new_c_s)    # add new client com socket

        # write setup packet to client, containing list of channel names
        pack.write_packet(new_c_s, pack.S_INIT, [c.query for c in self.channels])


    # run_server()
    # given a port, runs ( name ) server: writes file in pack.AUDIO_PACK
    # packets to client
    def run_server(self, num_channels=4):
        bitrate = 44100
        send_delay = (pack.AUDIO_PACK / 8) / bitrate

        print("We've initialized our server.")
        # Build list of playlists
        # Each playlist will be used for a channel
        # The first channel will be the lobby
        self.channels.append(Channel(LOBBY_QUERY, 1))
        for seed in get_seeds(num_channels):
            new_channel = Channel(seed, SONG_LIST_SIZE)
            if len(new_channel.songs) == 0:
                print(f"Channel failed to construct: {seed}")
                continue
            self.channels.append(new_channel)
        # self.channels.extend([Channel(seed, 2) for seed in get_seeds(num_channels)])

        self.print_channels()

        # TODO: while server doesn't recieve shutdown signal on STDIN
        while True:
            for channel in self.channels:
                self.write_song_packets(channel)

            # check for new clients and data from clients
            choices = [self.host_s] + self.clients
            rlist, _, _ = select.select(choices, [], [], 0)

            for s in rlist:
                # Server socket is ready to accept a new client
                if s is self.host_s:
                    self.connect_new_client()
                    self.print_channels()
                # if CLOSE_SERVER is entered on comand line, kill server
                # elif s is sys.stdin:
                #     str_in = sys.stdin.readline()[:-1]  # remove newline
                #     if str_in == CLOSE:
                #         return
                # else, Client socket sent data to be read
                else:
                    # msg = "Hello client!"     TODO: remove msg writing
                    # if pack.write_packet(s, pack.S_MSG, msg) == -1:
                    #     self.disconnect_client(channel, s)
                    type, data = pack.read_packet(s)  # read packet from s
                    if type != -1:
                        self.server_handle_packet(type, data, s)
            
            time.sleep(pack.SEND_DELAY)


print("We're about to enter main.")
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