import sys
import os
import random
import time
import tweepy
from dotenv import load_dotenv
import musicbrainzngs
import requests
import json
import re

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

# File to store song history
SONG_HISTORY_FILE = "song_history.json"

# Load song history from file
def load_song_history():
    try:
        if os.path.exists(SONG_HISTORY_FILE):
            with open(SONG_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))  # Use set for faster lookups
        return set()
    except Exception as e:
        print(f"❌ Error loading song history: {e}")
        return set()

# Save song history to file
def save_song_history(history):
    try:
        with open(SONG_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(history), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Error saving song history: {e}")

# Normalize song title to remove remix indicators
def normalize_song_title(title):
    # Remove common remix keywords and parentheses content
    remix_keywords = r'\b(Remix|Mix|Rehearsal|Live|Demo|Extended|Redux|Version|Edit|C\.V\.G\.|Ghosts|Multitrack)\b|\([^)]*\)'
    normalized = re.sub(remix_keywords, '', title, flags=re.IGNORECASE).strip()
    # Remove extra spaces
    normalized = ' '.join(normalized.split())
    return normalized if normalized else title

# Check if a song is a remix or alternate version
def is_remix_or_alternate(title):
    remix_indicators = [
        'remix', 'mix', 'rehearsal', 'live', 'demo', 'extended', 'redux',
        'version', 'edit', 'c.v.g.', 'ghosts', 'multitrack'
    ]
    title_lower = title.lower()
    return any(indicator in title_lower for indicator in remix_indicators)

# Fetch Random Michael Jackson Song from MusicBrainz (Avoid Repeats and Remixes)
def fetch_random_song_musicbrainz(max_attempts=10):
    try:
        artist_name = "Michael Jackson"
        results = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if not results or 'artist-list' not in results or not results['artist-list']:
            print(f"❌ Could not find artist '{artist_name}' on MusicBrainz.")
            return None

        # Get the first artist's ID
        artist_id = results['artist-list'][0]['id']
        print(f"✅ Found Artist ID: {artist_id}")

        # Load song history (normalized titles)
        song_history = load_song_history()
        print(f"📜 Song history contains {len(song_history)} songs.")

        # Browse recordings by the artist
        recordings_results = musicbrainzngs.browse_recordings(artist=artist_id, limit=100)
        if not recordings_results or 'recording-list' not in recordings_results or not recordings_results['recording-list']:
            print(f"❌ No songs found for {artist_name} on MusicBrainz.")
            return None

        recordings = recordings_results['recording-list']
        # Filter out remixes and songs already in history
        available_songs = [
            r.get("title") for r in recordings
            if r.get("title") and not is_remix_or_alternate(r.get("title"))
            and normalize_song_title(r.get("title")) not in song_history
        ]

        # If no available songs, try without remix filter or reset history
        if not available_songs:
            print("⚠️ No new non-remix songs available. Trying all songs.")
            available_songs = [
                r.get("title") for r in recordings
                if r.get("title") and normalize_song_title(r.get("title")) not in song_history
            ]
            if not available_songs:
                print("⚠️ All songs have been used. Resetting history.")
                song_history.clear()
                save_song_history(song_history)
                available_songs = [
                    r.get("title") for r in recordings
                    if r.get("title") and not is_remix_or_alternate(r.get("title"))
                ]
                if not available_songs:
                    available_songs = [r.get("title") for r in recordings if r.get("title")]

        # Try to select a new song
        for _ in range(max_attempts):
            if not available_songs:
                print("❌ No new songs available after filtering history.")
                return None

            song_title = random.choice(available_songs)
            normalized_title = normalize_song_title(song_title)
            if normalized_title not in song_history:
                # Add normalized title to history
                song_history.add(normalized_title)
                save_song_history(song_history)
                print(f"✅ Selected Song from MusicBrainz: {song_title} (Normalized: {normalized_title})")
                return song_title

            # Remove the song from available_songs to avoid re-selecting
            available_songs.remove(song_title)

        print(f"❌ Could not find a new song after {max_attempts} attempts.")
        return None

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
