import sys
import os
import random
import tweepy
from dotenv import load_dotenv
from musicxmatch_api import MusixMatchAPI
import json

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

# ✅ Authenticate Twitter API v2 (Tweet Creation)
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token=BEARER_TOKEN
)

# ✅ Initialize MusixMatchAPI
api = MusixMatchAPI()

# ------------------------------------------------
# ✅ Fetch Random Michael Jackson Song from Musixmatch
# ------------------------------------------------
def fetch_random_song():
    try:
        # Search for Michael Jackson's tracks
        search = api.search_tracks("Michael Jackson")

        if not search or "message" not in search:
            print("❌ No songs found on Musixmatch.")
            return None, None

        # Extract track list
        tracks = search["message"]["body"]["track_list"]
        if not tracks:
            print("❌ No songs found in track list.")
            return None, None

        # Randomly select a song
        random_track = random.choice(tracks)["track"]
        track_name = random_track["track_name"]
        track_id = random_track["track_id"]
        print(f"✅ Selected Song: {track_name} (ID: {track_id})")
        return track_name, track_id

    except Exception as e:
        print(f"❌ Error fetching song from Musixmatch: {e}")
        return None, None

# ------------------------------------------------
# ✅ Fetch Lyrics for a Specific Song from Musixmatch
# ------------------------------------------------
def fetch_lyrics(track_id):
    try:
        # Get the track lyrics
        search = api.get_track_lyrics(track_id=track_id)

        if not search or "message" not in search:
            print("❌ No lyrics found on Musixmatch.")
            return None

        # Extract lyrics
        lyrics = search["message"]["body"]["lyrics"]["lyrics_body"]
        if not lyrics:
            print("❌ Lyrics not available for this track.")
            return None

        # Randomly select 1-2 lines
        lines = [line.strip() for line in lyrics.split("\n") if line.strip()]
        selected_lines = random.sample(lines, min(len(lines), 2))

        return "\n".join(selected_lines)

    except Exception as e:
        print(f"❌ Error fetching lyrics from Musixmatch: {e}")
        return None

# ------------------------------------------------
# ✅ Post Tweet using Twitter API v2
# ------------------------------------------------
def post_tweet(content):
    try:
        response = client.create_tweet(text=content)
        tweet_id = response.data["id"]
        print(f"✅ Tweet posted successfully: https://twitter.com/user/status/{tweet_id}")
    except Exception as e:
        print(f"❌ Error posting tweet: {e}")

# ------------------------------------------------
# ✅ Main Execution
# ------------------------------------------------
if __name__ == "__main__":
    song_title, track_id = fetch_random_song()
    if song_title and track_id:
        lyrics = fetch_lyrics(track_id)
        if lyrics:
            post_tweet(f"🎵 {song_title}\n\n{lyrics}")
