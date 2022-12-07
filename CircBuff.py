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
    def __init__(self, len):
        # TODO: enforce non-negative length?
        self.buff_len = len
        self.circ_buff = [0] * len

        self.buff_head = self.buff_len # init
        self.buff_tail = 0

    # append()
        # append given data to the tail of circular buffer; assumes 
        # there's enough empty space in circ_buff to hold data, e.g.
        # checked with a call to sublen()
        # returns True if append is successful, False if buffer is full
    def append(self, data):
        len_data = len(data)

        # if buffer doesn't have enough room for len_data bytes
        if len_data > self.sublen(self.buff_tail, self.buff_head):
            return False

        # set buff_head to 0 after reset
        self.buff_head = self.buff_head % self.buff_len

        # if data will wrap around end of circ_buff
        if self.buff_tail + len_data > self.buff_len:
            bytes_to_end = self.buff_len - self.buff_tail

            # write this many bytes of data into end of circ_buff 
            self.circ_buff[self.buff_tail :] = data[: bytes_to_end]

            # write rest of data buffer into start of circ_buff
            self.circ_buff[: len_data - bytes_to_end] = data[bytes_to_end :]
            # set buff tail
            self.buff_tail = len_data - bytes_to_end
        else:
        # write data into circular buffer
            self.circ_buff[self.buff_tail : self.buff_tail + len_data] = data
            self.buff_tail = self.buff_tail + len_data

        return True

    # consume()
        # consumes num elements from circular buffer, shifting up
        # buff_head to match
        # returns data if sucessful, empty list if num > number of items
        # currently in CircBuffer
    def consume(self, num):
        if num > self.sublen(self.buff_head, self.buff_tail):
            return []
        
        if self.buff_head + num > self.buff_len:
            bytes_to_end = self.buff_len - self.buff_head

            # take this many bytes of data from end of circ_buff 
            got_data = self.circ_buff[self.buff_head :]
            # take rest of data from start of circ_buff
            more_data = self.circ_buff[: num - bytes_to_end]
            got_data = got_data + more_data
            # set buff_head
            self.buff_head = num - bytes_to_end
        else:
            got_data = self.circ_buff[self.buff_head : self.buff_head + num]

            self.circ_buff[self.buff_head : self.buff_head + num] = [0] * num
            self.buff_head = self.buff_head + num

        return got_data

    # reset()
        # clear circular buffer
    def reset(self):
        self.circ_buff = [0] * self.buff_len
        self.buff_head = self.buff_len # init
        self.buff_tail = 0


    # sublen()
        # gets number of elements from [from_ind, to_ind)
    def sublen(self, from_ind, to_ind):
        if to_ind == from_ind:
            return 0
        elif to_ind > from_ind:
            return to_ind - from_ind
        else:
            return (self.buff_len - from_ind) + to_ind + 1