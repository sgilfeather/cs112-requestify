# cs112: requestify

**Requestify** is a music streaming application which dynamically mixes and streams unique playlists based on user genre and mood ("vibe") requests.  The application consists of client-server network architecture. The `Server` endpoint generates a series of music channels, which stream song playlists generated from a list of genre seed. These channels are populated with songs downloaded through the Soundcloud API, and maintain an active list of which clients are listening to that channel. The `Client` endpoint sends genre requests to the Server and receives streamed audio data, playing it through the Client machine's speakers. Through its terminal-based UI, clients can join different channels; make "vibe" requests, to fine-tune the genre of songs on their channel; and, broadcast chat messages to other clients on their channel.

## Requirements

-   [Python 3.9](https://www.python.org/downloads/)

## Setup

1. Install Python requirements: `pip install -r requirements.txt`
2. Run the server: `python Server.py <port>`
3. Run the client: `python Client.py <server ip> <port>`
