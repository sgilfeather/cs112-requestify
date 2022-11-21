# cs112-soundcloud

## Setup

1. Install Python requirements: `pip install -r requirements.txt`
2. Create a `.env` file in the root directory of the project. It should contain
   your SoundCloud client ID in the following format:

    ```
    CLIENT_ID=YOUR_CLIENT_ID
    ```

## TODO
- [x] write testing in Test.py (choose package framework)
- [x] test CircBuff.py
- [ ] packet-writing module for client and server
- [ ] client requests song search name to be retrieved from SoundCloud
    - [ ] connect recieved SoundParser data to Server writing out

- [ ] potentially consume every other frame when we need to speed up?
