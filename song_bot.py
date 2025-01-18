import sys
import os
import random
import time
import tweepy
from dotenv import load_dotenv
from lyricsgenius import Genius
import requests

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

# ✅ Load Environment Variables
load_dotenv()

# ✅ API Credentials
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# ✅ Authenticate Twitter API v2 (Tweet Creation)
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token=BEARER_TOKEN
)

# ✅ Fetch Random Michael Jackson Song from Last.fm
def fetch_random_song_lastfm():
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=Michael+Jackson&api_key={LASTFM_API_KEY}&format=json"
        response = requests.get(url)
        response.raise_for_status()
        tracks = response.json().get("toptracks", {}).get("track", [])

        if not tracks:
            print("❌ No songs found on Last.fm.")
            return None

        # Randomly select a song from the top tracks
        random_track = random.choice(tracks)
        song_title = random_track.get("name")
        print(f"✅ Selected Song: {song_title}")
        return song_title
    except Exception as e:
        print(f"❌ Error fetching song from Last.fm: {e}")
        return None

# ✅ Fetch Random Michael Jackson Lyrics from Genius API
def fetch_genius_lyrics(genius_api_token, song_title):
    try:
        genius = Genius(genius_api_token)
        song = genius.search_song(song_title, "Michael Jackson")

        if not song or not song.lyrics:
            print("❌ No lyrics found in the Genius API.")
            return None

        # Split lyrics into lines, excluding empty lines and metadata
        lines = [line.strip() for line in song.lyrics.split("\n") if line.strip() and not line.startswith("[")]

        if not lines:
            print("❌ No valid lyrics lines found.")
            return None

        # Randomly select 1-2 lines
        selected_lines = random.sample(lines, min(len(lines), 2))

        return "\n".join(selected_lines)
    except Exception as e:
        print(f"❌ Error fetching lyrics from Genius API: {e}")
        return None

# ✅ Fetch Lyrics Dynamically
def fetch_random_lyrics():
    # Fetch a random song from Last.fm
    song_title = fetch_random_song_lastfm()

    if not song_title:
        print("❌ Could not fetch a song title. Exiting.")
        return None

    # Fetch lyrics for the song using Genius API
    return fetch_genius_lyrics(GENIUS_API_TOKEN, song_title)

# ✅ Post Tweet using Twitter API v2
def post_tweet(content):
    try:
        response = client.create_tweet(text=content)
        tweet_id = response.data["id"]
        print(f"✅ Tweet posted successfully: https://twitter.com/user/status/{tweet_id}")
    except Exception as e:
        print(f"❌ Error posting tweet: {e}")

# ✅ Main Execution
if __name__ == "__main__":
    lyrics = fetch_random_lyrics()
    if lyrics:
        post_tweet(lyrics)
