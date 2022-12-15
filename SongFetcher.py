#
# SongFetcher.py
# Tyler Thompson, CS112 Fall 2022
#
# Given a SoundCloud client ID, fetches 
#

import requests
import os
import dotenv
from pydub import AudioSegment
import ffmpeg
from urllib.parse import urlencode

SONG_DIR = "songs"
MAX_RETRIES = 5

# stubborn_get()
# Given a url for a GET req, attempts up to MAX_RETRIES GET requests for
# a successful response
def stubborn_get(url):
    response = requests.get(url, timeout=5)
    retries = 0

    while response.status_code != 200 and retries < MAX_RETRIES:
        response = requests.get(url, timeout=5)
        retries += 1
        if response.status_code != 200:
            print(f"Failed to get {url}, retrying")
    if retries == MAX_RETRIES:
        print(f"Failed to get {url} after {MAX_RETRIES} retries")

        # bad authentication: try to regenerate the CLIENT_ID key
        if response.status_code == 401:
            dotenv.unset_key(".env", "CLIENT_ID", quote_mode='always', encoding='utf-8')
            get_client_id()     # re-get client ID, scraped from SoundCloud


# sneaky_get()
# Given a url for a GET request, makes a GET request to that url with a fake
# user agent to avoid being blocked by SoundCloud
def sneaky_get(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    }
    response = requests.get(url, headers=headers, timeout=5)
    retries = 0

    while response.status_code != 200 and retries < MAX_RETRIES:
        print(f"Failed to get {url} after {retries} retries, trying again")
        # bad authentication: try to regenerate the CLIENT_ID key
        if response.status_code == 401:
            dotenv.unset_key(".env", "CLIENT_ID", quote_mode='always', encoding='utf-8')
            get_client_id()     # re-get client ID, scraped from SoundCloud
        
        response = requests.get(url, timeout=5)
        retries += 1

    return response


# search()
# given a search query and limit on max # of results to return, makes a GET
# req to the SoundCloud API
# returns a JSON response with elements:
def search(query, limit=10, genre=""):
    q_params = {
        "q": query,
        "limit": limit,
        "filter.genre_or_tag": genre,
        "filter.duration": "short",
        "client_id": get_client_id(),
    }
    url = f"https://api-v2.soundcloud.com/search/tracks?" + urlencode(q_params)
    response = sneaky_get(url)

    if response.status_code != 200:
        return []
    return response.json()["collection"]


# download_song()
# 
def download_song(track):
    if not os.path.exists(SONG_DIR):
        os.mkdir(SONG_DIR)
    
    # Use the track's id as the filename
    title = track["title"]
    id = track["id"]
    filename = f"{id}.mp3"
    filename_wav = f"{id}.wav"

    # print(f"Downloading: {title} ({id})")

    # Immediately return if the file was already downloaded
    if os.path.exists(os.path.join(SONG_DIR, filename)):
        # print(f"File {filename} already downloaded")
        return filename_wav

    q_params = {
        "client_id": get_client_id(),
    }
    transcode_url = track["media"]["transcodings"][0]["url"] + "?" + urlencode(q_params)
    response = sneaky_get(transcode_url)
    if response.status_code != 200:
        return None

    playlist_url = response.json()["url"]
    response = sneaky_get(playlist_url)
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
            response = sneaky_get(segment)
            if response.status_code == 200:
                f.write(response.content)
    
    # Convert the file to wav
    mp3_data = AudioSegment.from_mp3(os.path.join(SONG_DIR, filename))
    mp3_data.export(os.path.join(SONG_DIR, filename_wav), format="wav")
    
    print("Done")
    return filename_wav

def append_to_env(key, value):
    with open(".env", "a") as f:
        f.write(f"{key}={value}\n")

# Attempts to retreive a SoundCloud client ID
# First checks the .env file for a CLIENT_ID key
# If that fails, it attempts to scrape a client_id from the SoundCloud website
# If all fails, it will throw an exception
def get_client_id():
    # Try to get the client ID from the .env file
    client_id = dotenv.get_key(".env", "CLIENT_ID")
    if client_id:
        return client_id
    print("Trying to scrape client ID from SoundCloud")
    
    # Fall back to scraping the client ID from the SoundCloud website
    res = requests.get("https://soundcloud.com")

    # The link to the JS file with the client ID looks like this:
	# <script crossorigin src="https://a-v2.sndcdn.com/assets/sdfhkjhsdkf.js"></script
    urls = res.text.split("<script crossorigin src=\"")[1:]
    if len(urls) == 0:
        raise Exception("Could not find client ID")
    # It seems like our desired URL is always imported last
    target = urls[-1].split("\"></script>")[0]
    # fetch js file
    res = requests.get(target)
    # find client id
    if ",client_id:" in res.text:
        client_id = res.text.split(",client_id:\"")[1].split("\"")[0]
        print(f"Found client ID: {client_id}")
        append_to_env("CLIENT_ID", client_id)
        return client_id
    raise Exception("Could not find client ID")