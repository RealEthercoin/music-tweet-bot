import sys
import os
import random
import time
import tweepy
from dotenv import load_dotenv
import musicbrainzngs
import requests

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Load Environment Variables
load_dotenv()

# Validate API Credentials
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN]):
    print("❌ Missing one or more Twitter API credentials. Check your .env file.")
    sys.exit(1)

# Authenticate Twitter API v2
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token=BEARER_TOKEN
)

# Initialize MusicBrainz API
musicbrainzngs.set_useragent("MJLyricBot", "0.1", "thanayogesh23@gmail.com")

# Fetch Random Michael Jackson Song from MusicBrainz
def fetch_random_song_musicbrainz():
    try:
        artist_name = "Michael Jackson"
        results = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if not results or 'artist-list' not in results or not results['artist-list']:
            print(f"❌ Could not find artist '{artist_name}' on MusicBrainz.")
            return None

        # Get the first artist's ID
        artist_id = results['artist-list'][0]['id']
        print(f"✅ Found Artist ID: {artist_id}")

        # Browse recordings by the artist
        recordings_results = musicbrainzngs.browse_recordings(artist=artist_id, limit=100)
        if not recordings_results or 'recording-list' not in recordings_results or not recordings_results['recording-list']:
            print(f"❌ No songs found for {artist_name} on MusicBrainz.")
            return None

        random_recording = random.choice(recordings_results['recording-list'])
        song_title = random_recording.get("title")
        if not song_title:
            print("❌ No title found for the selected recording.")
            return None

        print(f"✅ Selected Song from MusicBrainz: {song_title}")
        return song_title

    except musicbrainzngs.WebServiceError as e:
        print(f"❌ MusicBrainz WebServiceError: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error in fetch_random_song_musicbrainz: {e}")
        return None

# Fetch Lyrics from Lyrics.ovh
def fetch_lyrics_lyrics_ovh(song_title, artist_name="Michael Jackson"):
    try:
        base_url = "https://api.lyrics.ovh/v1"
        # Replace spaces with %20 for URL encoding
        artist_name_encoded = artist_name.replace(" ", "%20")
        song_title_encoded = song_title.replace(" ", "%20")
        url = f"{base_url}/{artist_name_encoded}/{song_title_encoded}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "lyrics" not in data or not data["lyrics"].strip():
            print(f"❌ No lyrics found for '{song_title}' on Lyrics.ovh.")
            return None

        lyrics = data["lyrics"].strip()
        # Split lyrics into lines, exclude empty lines
        lines = [line.strip() for line in lyrics.split("\n") if line.strip()]
        if not lines:
            print(f"❌ No valid lyrics lines found for '{song_title}'.")
            return None

        # Select 1-2 consecutive lines, ensuring they fit within 280 characters
        max_chars = 280
        # Choose a random starting index, ensuring we have room for at least 1 line
        start_index = random.randint(0, len(lines) - 1)
        selected_lines = [lines[start_index]]

        # Try to add the next line if it exists and fits
        if start_index + 1 < len(lines):
            next_line = lines[start_index + 1]
            if len("\n".join(selected_lines + [next_line])) <= max_chars:
                selected_lines.append(next_line)

        if not selected_lines:
            print(f"❌ Could not select lyrics within 280 characters for '{song_title}'.")
            return None

        result = "\n".join(selected_lines)
        print(f"✅ Selected consecutive lyrics for '{song_title}':\n{result}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching lyrics from Lyrics.ovh for '{song_title}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error in fetch_lyrics_lyrics_ovh for '{song_title}': {e}")
        return None

# Fetch Random Lyrics
def fetch_random_lyrics(max_attempts=3):
    for attempt in range(max_attempts):
        song_title = fetch_random_song_musicbrainz()
        if not song_title:
            print(f"❌ Attempt {attempt + 1}/{max_attempts}: Could not fetch song title.")
            continue

        lyrics = fetch_lyrics_lyrics_ovh(song_title)
        if lyrics:
            print(f"✅ Fetched lyrics for '{song_title}':\n{lyrics}")
            return lyrics

        print(f"❌ Attempt {attempt + 1}/{max_attempts}: No lyrics found for '{song_title}'.")
        time.sleep(1)  # Avoid overwhelming the API

    print(f"❌ Failed to fetch lyrics after {max_attempts} attempts.")
    return None

# Post Tweet
def post_tweet(content):
    try:
        if len(content) > 280:
            print(f"❌ Tweet content exceeds 280 characters: {len(content)} characters.")
            return

        response = client.create_tweet(text=content)
        tweet_id = response.data["id"]
        print(f"✅ Tweet posted successfully: https://twitter.com/user/status/{tweet_id}")

    except tweepy.TweepyException as e:
        print(f"❌ Error posting tweet: {e}")
    except Exception as e:
        print(f"❌ Unexpected error in post_tweet: {e}")

# Main Execution
if __name__ == "__main__":
    lyrics = fetch_random_lyrics()
    if lyrics:
        post_tweet(lyrics)
    else:
        print("❌ Could not fetch lyrics. Tweet not posted.")
