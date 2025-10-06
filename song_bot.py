#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, time, random, requests, tweepy, sys, json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# --- Configuration ---
MJ_MBID = "f27ec8db-af05-4f36-916e-3d57f91ecf5e"  # Michael Jackson MusicBrainz ID
USER_AGENT = "MJTweetBot/1.0 (thanayogesh23@gmail.com)"
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Google Custom Search API key
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")  # Google Custom Search Engine ID

USED_SONGS_FILE = "used_songs.txt"
NO_LYRICS_FILE = "no_lyrics_songs.txt"
RECORDINGS_FILE = "recordings.json"

SKIP_TITLE_KEYWORDS = [
    "remix", "version", "edit", "live", "instrumental", "karaoke",
    "demo", "bonus", "acoustic", "reprise", "mix"
]

# Verify environment variables
if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN, GOOGLE_API_KEY, GOOGLE_CSE_ID]):
    print("❌ Missing one or more API credentials. Check your .env file.")
    sys.exit(1)
print("✅ API credentials loaded successfully")

# --- Helpers ---

def normalize_title(title):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', '', title.lower())).strip()

def load_used_songs(filename):
    if not os.path.isfile(filename):
        print(f"⚠️ {filename} not found, starting with empty used songs list")
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        used = {line.strip() for line in f}
        print(f"📖 Loaded {len(used)} used songs from {filename}")
        return used

def save_used_song(filename, title_key):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(title_key + "\n")
    print(f"💾 Saved song to used_songs: {title_key}")

def load_no_lyrics(filename):
    if not os.path.isfile(filename):
        print(f"⚠️ {filename} not found, starting with empty no lyrics list")
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        no_lyrics = {line.strip() for line in f}
        print(f"📖 Loaded {len(no_lyrics)} no lyrics songs from {filename}")
        return no_lyrics

def save_no_lyrics(filename, title_key):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(title_key + "\n")
    print(f"💾 Saved song to no_lyrics: {title_key}")

# --- Image Fetching ---

def fetch_mj_image(query="Michael Jackson"):
    print(f"🖼️ Fetching image for query: {query}")
    try:
        # Initialize Google Custom Search API
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        result = service.cse().list(
            q=query,
            cx=GOOGLE_CSE_ID,
            searchType="image",  # Restrict to image search
            num=3  # Fetch 3 images to choose from
        ).execute()
        
        images = result.get("items", [])
        if not images:
            print("⚠️ No images found via Google CSE")
            return None
        
        # Select a random image
        image_url = random.choice(images)["link"]
        print(f"✅ Found image: {image_url}")
        
        # Download the image
        img_resp = requests.get(image_url, headers={"User-Agent": USER_AGENT}, timeout=5)
        img_resp.raise_for_status()
        img_path = "temp_mj_image.jpg"
        with open(img_path, "wb") as f:
            f.write(img_resp.content)
        print(f"💾 Downloaded image to {img_path}")
        
        # Verify file size (Twitter limit: 5MB)
        if os.path.getsize(img_path) > 5 * 1024 * 1024:
            print("⚠️ Image too large for Twitter (>5MB)")
            os.remove(img_path)
            return None
            
        return img_path
    except HttpError as e:
        print(f"❌ Google CSE API error: {e}")
        return None
    except Exception as e:
        print(f"❌ Image fetch error: {e}")
        return None

# --- Recordings Fetch & Cache ---

def fetch_and_cache_recordings():
    recordings = []
    offset = 0
    limit = 100
    while True:
        url = (
            f"https://musicbrainz.org/ws/2/recording?query=arid:{MJ_MBID}"
            f"&limit={limit}&offset={offset}&fmt=json"
        )
        print(f"🌐 Fetching recordings from: {url}")
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            recs = [rec["title"] for rec in data.get("recordings", [])]
            recordings.extend(recs)
            print(f"✅ Fetched {len(recs)} recordings, total so far: {len(recordings)}")
            count = data.get("count", 0)
            if offset + limit >= count:
                break
            offset += limit
            time.sleep(1)  # respect MusicBrainz rate limit
        except Exception as e:
            print(f"❌ MusicBrainz API error: {e}")
            break
    
    with open(RECORDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(recordings, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(recordings)} recordings to {RECORDINGS_FILE}")
    return recordings

def load_recordings():
    if os.path.isfile(RECORDINGS_FILE):
        with open(RECORDINGS_FILE, "r", encoding="utf-8") as f:
            recordings = json.load(f)
        print(f"📖 Loaded {len(recordings)} recordings from {RECORDINGS_FILE}")
        return recordings
    else:
        print("⚠️ No cached recordings found, fetching fresh list")
        return fetch_and_cache_recordings()

# --- Lyrics fetching ---

def fetch_lyrics_primary(artist, title):
    normalized_title = normalize_title(title)
    url = f"https://api.lyrics.ovh/v1/{artist}/{normalized_title}"
    print(f"🎵 Fetching lyrics (primary) for: {artist} - {title} (URL: {url})")
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            print(f"⚠️ Lyrics API (primary) returned status {resp.status_code} for {title}")
            return None
        lyrics = resp.json().get("lyrics")
        if not lyrics:
            print(f"⚠️ No lyrics found (primary) for {title}")
        return lyrics
    except Exception as e:
        print(f"❌ Lyrics API (primary) error for {title}: {e}")
        return None

def fetch_lyrics_fallback(artist, title):
    az_title = re.sub(r'[^a-z0-9]', '', title.lower())
    url = f"https://www.azlyrics.com/lyrics/{artist.lower().replace(' ', '')}/{az_title}.html"
    print(f"🎵 Fetching lyrics (fallback) for: {artist} - {title} (URL: {url})")
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
        if resp.status_code != 200:
            print(f"⚠️ Lyrics fallback returned status {resp.status_code} for {title}")
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        ringtone = soup.find("div", class_="ringtone")
        if ringtone:
            lyrics_div = ringtone.find_next_sibling("div")
            if lyrics_div:
                lyrics = lyrics_div.text.strip()
                if lyrics:
                    return lyrics
        print(f"⚠️ No lyrics found (fallback) for {title}")
        return None
    except Exception as e:
        print(f"❌ Lyrics fallback error for {title}: {e}")
        return None

def fetch_lyrics(artist, title):
    lyrics = fetch_lyrics_primary(artist, title)
    if lyrics:
        return lyrics
    return fetch_lyrics_fallback(artist, title)

# --- Processing lyrics ---

def clean_lyrics(raw):
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" in line or "[" in line or "]" in line:
            continue
        lines.append(line)
    print(f"🧹 Cleaned lyrics: {len(lines)} lines")
    return lines

def select_snippet(lines):
    if len(lines) < 2:
        print("⚠️ Not enough lines for snippet")
        return None
    for num in (3, 2):
        if len(lines) < num:
            continue
        start = random.randint(0, len(lines) - num)
        snippet = "\n".join(lines[start:start+num])
        tweet_text = snippet + "\n#MichaelJackson"
        if len(tweet_text) <= 280:
            print(f"✅ Selected snippet: {tweet_text}")
            return tweet_text
    snippet = "\n".join(lines[:2])
    tweet_text = snippet + "\n#MichaelJackson"
    print(f"🔄 Fallback snippet: {tweet_text}")
    return tweet_text if len(tweet_text) <= 280 else None

# --- Twitter ---

def tweet_lyric_with_image(text, image_path):
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
        bearer_token=BEARER_TOKEN
    )
    # Initialize Tweepy API for media upload (v1.1 API required for media)
    auth = tweepy.OAuth1UserHandler(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    api = tweepy.API(auth)
    
    print(f"📤 Attempting to tweet: {text} with image: {image_path}")
    try:
        # Upload media
        media = api.media_upload(image_path)
        # Post tweet with media
        client.create_tweet(text=text, media_ids=[media.media_id])
        print("✅ Tweet with image posted successfully")
        # Clean up temporary image file
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"🗑️ Removed temporary image: {image_path}")
        return True
    except Exception as e:
        print(f"❌ Tweepy error: {e}")
        return False

# --- Main ---

def main():
    print("🚀 Starting MJ Tweet Bot")
    used_songs = load_used_songs(USED_SONGS_FILE)
    no_lyrics_songs = load_no_lyrics(NO_LYRICS_FILE)
    random.seed()

    recordings = load_recordings()
    if not recordings:
        print("❌ No recordings available. Exiting.")
        return

    print(f"🔢 Total recordings: {len(recordings)}")

    # Filter usable songs
    possible = []
    for title in recordings:
        if any(key in title.lower() for key in SKIP_TITLE_KEYWORDS):
            continue
        key = normalize_title(title)
        if key in used_songs or key in no_lyrics_songs:
            continue
        possible.append(title)
    
    if not possible:
        print("🔄 No more unused songs with lyrics available. Resetting used songs list.")
        open(USED_SONGS_FILE, "w").close()
        used_songs = set()
        possible = [t for t in recordings if normalize_title(t) not in no_lyrics_songs]

    random.shuffle(possible)

    for title in possible:
        print(f"🎵 Processing song: {title}")
        key = normalize_title(title)

        # Fetch lyrics
        lyrics = fetch_lyrics("Michael Jackson", title)
        if not lyrics:
            print(f"⚠️ No lyrics found for {title}, marking as no lyrics")
            save_no_lyrics(NO_LYRICS_FILE, key)
            continue

        # Select tweet snippet
        snippet = select_snippet(clean_lyrics(lyrics))
        if not snippet:
            print(f"⚠️ No valid snippet for {title}, moving to next song")
            continue

        # Fetch image
        image_path = fetch_mj_image(f"Michael Jackson {title}")
        if not image_path:
            print(f"⚠️ No image found for {title}, skipping to next song")
            continue

        # Tweet with image
        if tweet_lyric_with_image(snippet, image_path):
            save_used_song(USED_SONGS_FILE, key)
            print(f"🎉 Successfully tweeted for {title}")
            break
        else:
            print(f"❌ Failed to tweet for {title}, moving to next song")
            # Clean up image if tweet failed
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"🗑️ Removed temporary image: {image_path}")

    print("🏁 Script completed")

if __name__ == "__main__":
    main()
