#
# PACKET.PY
# (Soundcloud / Application name ) CS112, Fall 2022
#
#
# PACKET: (length) (type) (bytes)
#   type 1 = audio data
#   type 2 = channel list
#

import socket
import json
import binascii
from math import floor

PACK_SIZE = 1024 * 4
DATA_SIZE = PACK_SIZE - 5
BUFF_SIZE = PACK_SIZE * 200

# read_packet()
# reads a single frame from server on a given socket, this_sock; then,
# returns the recieved packet's type and payload
def read_packet(this_sock):
    if not isinstance(this_sock, socket.socket):
        print(f"Error: socket {this_sock} not initialized")
        return -1, ""

    type = -1
    data = ""
    try:
        header = this_sock.recv(5) # read header
        pack_size = int.from_bytes(header[:4], 'big')
        data = this_sock.recv(pack_size - 5) # make list
        if len(data) == 0: # no data recieved at this moment, return
            return 0, ""

        # full_pack_len = int.from_bytes(data[:4], 'big')

        type = int(header[4])
        # data = data[5:full_pack_len]
    # client connection may have dropped out
    except Exception as e:
        print(f"Error: cannot process packet. Source: {str(e)}.")
        return -1, ""

    # TODO: validate type to payload (data) type
    return type, data


# write_packet()
# given a packet type and payload of data, write packets of size PACK_SIZE
# until all data is sent
# returns True if packets are transmitted successfully, False otherwise
#
def write_packet(this_sock, type, data):
    if not isinstance(this_sock, socket.socket):
        print(f"Error: socket {this_sock} not initialized")
        return False
    # TODO: enforce that data is DATA_SIZE or less?

    packet_list = [0, 0, 0, 0, type]

    # data is type audio bytes
    if type == 1: 
        byte_list = list(data)
        packet_list.extend(byte_list)
    elif type == 2:
        byte_list = list(data.encode())
        packet_list.extend(byte_list)

    packet_list[:4] = len(packet_list).to_bytes(4, 'big')
    packet_bytes = bytes(packet_list)
    try:
        this_sock.send(packet_bytes);
    except Exception as e:
        # Client probably disconnected
        return False

    return True