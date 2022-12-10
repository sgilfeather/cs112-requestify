#
# PACKET.PY
# (Soundcloud / Application name ) CS112, Fall 2022
#
#
# Each packet is structured as follows:
#   [ data len, DATA_BYTE bytes ] [ json data, data len bytes]
#
# SERVER PACKETS:
#   Type 1: Init / Setup. Contains list of channels:
#       [ "channel_1", ...  "channel_num"]
#   
#
# CLIENT PACKETS: 
#   Type 2: Init / Setup. Contains port for comm channel and chosen channel,
#   if a channel has been selected
#       [ communication port ]
#
#

import socket
import json
from math import floor


BITRATE = 44100
DATA_BYTE = 2   # number of bytes in header to describe pack length
AUDIO_PACK = 1024
SEND_DELAY = ((AUDIO_PACK / 8) / BITRATE) / 2

# packet types
S_INIT = 1
C_INIT = 2
S_MSG = 3
C_MSG = 4

C_JOIN = 5
C_LIST = 6


# construct_packet()
# given an integer type and JSON-friendly data, construct a JSON packet
# and convert it into a byte packet
def construct_packet(type, data):
    json_bytes = ""
    try:
        json_str = json.dumps({"t":type, "d":data})
        json_bytes = bytes(json_str, 'utf-8')
    except TypeError as te:
        print(f"Cannot send data: invalid data type for packet.")
        return b"\0"   # null

    # data is type audio bytes
    max_bytes = (2 ** (8 * DATA_BYTE) - 1)
    if len(json_bytes) > max_bytes:
        print(f"Cannot send data: length {len(json_bytes)} exceeds max packet size {max_bytes}")
        return b"\0"   # null

    len_bytes = len(json_bytes).to_bytes(DATA_BYTE, 'big')
    return len_bytes + json_bytes


# construct_packet()
# given a byte string type containing JSON data, deconstruct it back into
# a JSON object, returning the "type" and "data" values from this JSON
def deconstruct_packet(packet_bytes):
    try:
        json_str = packet_bytes.decode('utf-8')
        json_data = json.loads(json_str)
        return json_data["t"], json_data["d"]
    except json.JSONDecodeError as je:
        print(f"Error: packet not JSON. Source: {je}")
        return -1, ""
    # packet is badly formatted
    except KeyError as ke:
        print(f"Error: packet badly formattted. Packet: {data}")
        return -1, ""
    # client connection may have dropped out
    except Exception as e:
        print(f"Error: cannot process packet. Source: {e}.")
        return -1, ""


# read_packet()
# reads a single frame from server on a given socket, this_sock; then,
# returns the recieved packet's type and payload
def read_packet(this_sock):
    if not isinstance(this_sock, socket.socket):
        print(f"Error: socket {this_sock} not initialized")
        return -1, ""

    try:    # first, read the packet from stream
        frame = this_sock.recv(DATA_BYTE)
        if len(frame) == 0: # no data recieved at this moment, return
            return 0, ""

        # recieve full header
        while len(frame) < DATA_BYTE:
            frame += this_sock.recv(DATA_BYTE - len(frame))

        packet_len = int.from_bytes(frame, 'big')

        # now, read packet in entirety
        packet_bytes =  this_sock.recv(packet_len)
        while len(packet_bytes) < packet_len:
            packet_bytes += this_sock.recv(packet_len - len(packet_bytes))  

    except Exception as e:
        print(f"Error: can not read packet. Source: {str(e)}.")
        return -1, ""

    # now, decode the packet into JSON; returns type, data
    return deconstruct_packet(packet_bytes)


# write_packet()
# given a packet type and payload of data, write packets of size PACK_SIZE
# until all data is sent
# returns True if packets are transmitted successfully, False otherwise
#
def write_packet(this_sock, type, data):
    if not isinstance(this_sock, socket.socket):
        print(f"Error: socket {this_sock} not initialized")
        return False

    packet_bytes = construct_packet(type, data)
    if packet_bytes == b"\0":
        return False

    try:
        sent = this_sock.send(packet_bytes);
        while sent < len(packet_bytes):
            new_sent = this_sock.send(packet_bytes[sent:])
            sent = sent + new_sent
    except Exception as e:
        print(f"Error: can not write packet. Source: {str(e)}.")
        return False

    return True