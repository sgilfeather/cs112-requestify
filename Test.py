#
# TEST.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Helper to unit-test ( name ) functions
#

import sys
import socket
import Packet as packet

def init_client_server(port):
    try:
        # set up server
        s_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_s.bind(( "127.0.0.1", port))
        s_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_s.listen()

        # set up client
        c_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c_s.connect(("127.0.0.1", port))

        s_to_c, _ = s_s.accept()

        return c_s, s_s, s_to_c     # return client, server socket descriptors
    except Exception as e:
        print(f"Error: could not initialize client and server. Source: {str(e)}")
        return -1, -1


def close_client_server(c_s, s_s, s_to_c):
    try:
        c_s.close()
        s_s.close()
    except Exception as e:
        print(f"Error: could not close client and server. Source: {str(e)}")


def test_packet(port):
    # test construct and deconstruct
    pack_bytes = packet.construct_packet(1, [8000, 2, "lofi", "hiphop"])
    print(pack_bytes)

    pack_bytes = pack_bytes[packet.DATA_BYTE:] # throw out len header
    out_type, out_data = packet.deconstruct_packet(pack_bytes)
    print(f"Got type {out_type} and data {out_data}")

    # test sending over client server
    
    c_s, s_s, s_to_c = init_client_server(port)
    packet.write_packet(s_to_c, out_type, out_data)
    read_type, read_data = packet.read_packet(c_s)
    print(f"Client read type {read_type} and data {read_data}")

    close_client_server(c_s, s_s, s_to_c)

def spawn_multi_clients():
    # Fork 10 child processes to test packet sending
    import os
    for _ in range(10):
        pid = os.fork()
        if pid == 0:
            # Run Client.py
            os.execlp("python3", "python3", "Client.py", sys.argv[1], sys.argv[2])
        else:
            print(f"Started child process {pid}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 Test.py <server address> <port>")
        quit()

    spawn_multi_clients()
    # test_packet(int(sys.argv[1]))

if __name__ == "__main__":
    main()
