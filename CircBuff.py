#
# SERVER.PY
# (Soundcloud / Application name )
# Skylar Gilfeather, CS112 Fall 2022
# 
# Implementation of circular buffer for Client class; will be made private
# inner class after testing.

#!/usr/bin/python3

# 
# inner class CircBuff: 
# (description)
class CircBuff:
    def __init__(len):
        # TODO: enforce non-negative length?
        self.circ_buff = [0] * len
        self.buff_len = len

    # append()
        # append given data to the tail of circular buffer; assumes 
        # there's enough empty space in circ_buff to hold data, e.g.
        # checked with a call to sublen()
    def append(self, data, len_data):
        # if data will wrap around end of circ_buff
        if self.buff_tail + len_data > BUFF_SIZE:
            bytes_to_end = BUFF_SIZE - self.buff_tail

            # write this many bytes of data into end of circ_buff 
            circ_buff[self.buff_tail :] = data[: bytes_to_end]

            # write rest of data buffer into start of circ_buff
            circ_buff[: len_data - bytes_to_end] = data[bytes_to_end :]
        else:
        # write data into circular buffer
            circ_buff[self.buff_tail : self.buff_tail + len_data] = data


    # sublen()
        # gets number of elements from [from_ind, to_ind)
    def sublen(from_ind, to_ind):
        len = from_ind - to_ind
        return (len if len >= 0 else len + BUFF_SIZE)