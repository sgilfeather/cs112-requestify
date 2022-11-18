#
# SongFetcher.py
# Tyler Thompson, CS112 Fall 2022
#
# Given a SoundCloud client ID, fetches 
#

import json
import requests
import os
import dotenv
from pydub import AudioSegment

MAX_RETRIES = 10
SONG_DIR = "songs"
CLIENT_ID = dotenv.get_key(".env", "CLIENT_ID")

# stubborn_get()
# Given a url for a GET req, attempts up to MAX_RETRIES GET requests for
# a successful response
def stubborn_get(url):
    response = requests.get(url)
    retries = 0
    while response.status_code != 200 and retries < MAX_RETRIES:
        response = requests.get(url)
        retries += 1
    return response

# search()
# given a search query and limit on max # of results to return, makes a GET
# req to the SoundCloud API
# returns a JSON response with elements:
def search(query, limit=10):
    url = f"https://api-v2.soundcloud.com/search/tracks?q={query}&client_id={CLIENT_ID}&limit={limit}"
    response = stubborn_get(url)
    return response.json()


# download_song()
# 
def download_song(track):
    if not os.path.exists(SONG_DIR):
        os.mkdir(SONG_DIR)
    
    # Use the track's id as the filename
    title = track["title"]
    id = track["id"]
    filename = f"{id}.mp3"

    print(f"Downloading: {title} ({id})")

    # Immediately return if the file was already downloaded
    if os.path.exists(os.path.join(SONG_DIR, filename)):
        print(f"File {filename} already downloaded")
        return filename

    transcode_url = track["media"]["transcodings"][0]["url"] + "?client_id=" + CLIENT_ID
    response = stubborn_get(transcode_url)
    if response.status_code != 200:
        return None

    playlist_url = response.json()["url"]
    response = stubborn_get(playlist_url)
    if response.status_code != 200:
        return None
    
    # Each playlist item is a different line in the response
    playlist = response.content.split(b"\n")
    
    # Merge all the segments into one file
    with open(os.path.join(SONG_DIR, filename), "wb") as f:
        for segment in playlist:
            # Skip lines that start with a #
            # These are comments
            if segment.startswith(b"#"):
                continue
            response = stubborn_get(segment)
            if response.status_code == 200:
                f.write(response.content)
    
    # Convert the file to wav
    mp3_data = AudioSegment.from_mp3(os.path.join(SONG_DIR, filename))
    filename_wav = f"{id}.wav"
    mp3_data.export(os.path.join(SONG_DIR, filename_wav), format="wav")
    
    print("Done")
    return filename
    
# MAIN: searches for a given artist 
    # TODO: update eminem to artist, bpm, or genre requested by Client

res = search("eminem", 1)
print(json.dumps(res))
for track in res["collection"]:
    title = track["title"]
    filename = download_song(track)
    if filename is None:
        print(f"Failed to download {title}")
