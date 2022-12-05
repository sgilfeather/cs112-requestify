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

PACK_SIZE = 1024
DATA_SIZE = PACK_SIZE - 5
BUFF_SIZE = PACK_SIZE * 4

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
        frame = this_sock.recv(PACK_SIZE) # make list
        if len(frame) == 0: # no data recieved at this moment, return
            return 0, ""

        full_pack_len = int.from_bytes(frame[:4], 'big')

        type = frame[4]
        data = frame[5:]
        print(data)
    except json.JSONDecodeError as je:
        print(f"Error: packet not JSON. Source: {je}")
        return -1, ""
    # packet is badly formatted
    except KeyError as ke:
        print(f"Error: packet badly formattted. Source: {str(data)}")
        return -1, ""
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

    packet_list[:4] = len(packet_list).to_bytes(4, 'big')
    packet_bytes = bytes(packet_list)
    try:
        this_sock.send(packet_bytes);
    except Exception as e:
        print(f"Error: can not write packet. Source: {str(e)}.")

    return True