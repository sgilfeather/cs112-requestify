# cs112-soundcloud

## Requirements

-   [Python 3.11](https://www.python.org/downloads/)

## Setup

1. Install Python requirements: `pip install -r requirements.txt`
2. Run the server: `python Server.py <port>`
3. Run the client: `python Client.py <server ip> <port>`

## TODO

-   [x] write testing in Test.py (choose package framework)
-   [x] test CircBuff.py
-   [ ] packet-writing module for client and server
-   [ ] client requests song search name to be retrieved from SoundCloud

    -   [ ] connect recieved SoundParser data to Server writing out

-   [ ] potentially consume every other frame when we need to speed up?
