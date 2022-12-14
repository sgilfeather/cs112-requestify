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
CLOSE = "exit"
SONG_LIST_SIZE = 2


# get_seeds()
# parses seed file in project root directory, and returns the first
# num_seeds seeds extracted.
#
def get_seeds(num_seeds):
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r") as f:
            seeds = f.read().splitlines()
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
    clients: list   # current clients: (comm sock, aud sock)
    open_file: BufferedReader   # current open song file

    def __init__(self, query, num_songs=SONG_LIST_SIZE):
        self.songs = []
        self.query = query
        self.clients = []
        self.open_file = None
        print(f"new channel: {query}")
        
        self.fill(num_songs)

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
        self.client_map = {}    # maps client com c_s's to audio c_s's
        self.name_map = {}     # maps client audio c_s's to their name

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
        # TODO: make faster
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
        for (com_sock, aud_sock) in channel.clients:
            try:
                num_sent = aud_sock.send(data)
                return num_sent
            except Exception:
                print(f"Client disconnected")
                self.disconnect_client(channel, com_sock)
                self.print_channels()


    def broadcast_chat(self, msg, client_socks):
        # TODO: make faster
        for channel in self.channels:
            if client_socks in channel.clients:     # broadcast to this Channel
                for (com_sock, aud_sock) in channel.clients:
                    full_msg = f"<{self.name_map[aud_sock]}> {msg}"
                    pack.write_packet(com_sock, pack.S_MSG, full_msg)
                break


    # help_handle_cinit
    # handles C_INIT packet
    def help_handle_cinit(self, data, this_sock):
        # data[0] is "com" or "aud", data[1] is temp nonce, data[2] is name
        if data[1] == "com" and data[2] in self.name_map.values():
            pack.write_packet(this_sock, S_ERR, "Username " + data[2] + " already taken.")
            return  # don't save if name taken, force client to resend

        nonce = data[1]
        name = data[2]
        # if nonce value is in map, finish the com : audio mapping
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
            self.name_map[aud_sock] = name
            self.print_channels()
        else:
            # map nonce to first socket, and type of first socket
            self.client_map[nonce] = [data[0], this_sock]


    # server_handle_packet()
    # given a packet recieved from the client,
    def server_handle_packet(self, type, data, com_sock):
        if type == pack.C_INIT:
            self.help_handle_cinit(data, com_sock)

        elif type == pack.C_JOIN:
            aud_sock = self.client_map[com_sock]
            for channel in self.channels:
                if channel.query == data:
                    self.move_client((com_sock, aud_sock), channel)
                    return
                    
        elif type == pack.C_LIST:
            # send list of channels to client
            pack.write_packet(com_sock, pack.S_LIST, [channel.query for channel in self.channels])

        elif type == pack.C_REQ:
            # No request query given
            if len(data) == 0:
                return
            aud_sock = self.client_map[com_sock]
            for channel in self.channels:
                if (com_sock, aud_sock) in channel.clients:
                    channel.query = data
                    channel.songs = []
                    channel.next()
                    break
            pack.write_packet(com_sock, pack.S_LIST, [channel.query for channel in self.channels])
            self.print_channels()

        elif type == pack.C_MSG:
            self.broadcast_chat(data, (com_sock, self.client_map[com_sock]))

    # disconnect_client
    # removes a client from the given channel, and from the server
    # TODO: error checking on closing c_s?
    def disconnect_client(self, channel, com_sock):
        # Try to find socket in client_map
        aud_sock = self.client_map[com_sock]
        channel.clients.remove((com_sock, aud_sock))
        self.clients.remove(com_sock)
        self.clients.remove(aud_sock)
        self.client_map.pop(com_sock)
        com_sock.close()
        aud_sock.close()
        # remove client if they disconnect
        print(f"Client disconnected")


    # connect_new_client()
    # accept a new client, add them to the lobby channel, and send them the
    # initial setup packet (before writing any audio data to them)
    def connect_new_client(self):
        new_c_s, c_addr = self.host_s.accept()
        self.clients.append(new_c_s)    # add new client com socket

        # write setup packet to client, containing list of channel names
        # and list of current client usernames
        names = list(self.name_map.values())
        data = {"c":[c.query for c in self.channels], "n":names}
        pack.write_packet(new_c_s, pack.S_INIT, data)


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
            choices = [self.host_s, sys.stdin] + self.clients
            rlist, _, _ = select.select(choices, [], [], 0)

            for s in rlist:
                # Server socket is ready to accept a new client
                if s is self.host_s:
                    self.connect_new_client()
                # if CLOSE_SERVER is entered on comand line, kill server
                elif s is sys.stdin:
                    str_in = sys.stdin.readline().lower()[:-1]
                    if str_in == CLOSE:
                        return
                else:
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