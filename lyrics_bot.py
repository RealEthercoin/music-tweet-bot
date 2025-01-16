import requests
import tweepy
import os
import random
import time
from dotenv import load_dotenv
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.audio.AudioClip import concatenate_audioclips
from PIL import Image, ImageDraw, ImageFont
import logging

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load Environment Variables
load_dotenv()

# Validate Environment Variables
required_env_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BEARER_TOKEN", "LASTFM_API_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        logging.error(f"Environment variable {var} is not set.")
        exit(1)

# API Credentials
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# Authenticate Twitter API v1.1 (Media Uploads)
auth_v1 = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth_v1)

# Authenticate Twitter API v2 (Tweet Creation)
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token=BEARER_TOKEN
)

# Paths
VIDEO_OUTPUT = "song_video.mp4"
AUDIO_OUTPUT = "audio_preview.m4a"
IMAGE_OUTPUT = "lyric_image.png"

# Fetch Trending Song
def fetch_trending_song():
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=chart.gettoptracks&api_key={LASTFM_API_KEY}&format=json"
        logging.debug(f"Fetching trending song from LastFM API: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        tracks = data.get("tracks", {}).get("track", [])
        if not tracks:
            logging.warning("No tracks found in the response.")
            return None, None
        random_track = random.choice(tracks)
        song_title = random_track.get("name", "Unknown Song")
        artist = random_track.get("artist", {}).get("name", "Unknown Artist")
        logging.info(f"Selected Song: {song_title} by {artist}")
        return song_title, artist
    except Exception as e:
        logging.error(f"Error fetching song: {e}")
        return None, None

# Fetch Album Cover
def fetch_album_cover(song_title, artist):
    try:
        url = f"https://itunes.apple.com/search?term={artist} {song_title}&media=music"
        logging.debug(f"Fetching album cover from iTunes API: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['results'][0].get('artworkUrl100')
    except Exception as e:
        logging.error(f"Error fetching album cover: {e}")
        return None

# Fetch Audio Preview
def fetch_audio_preview(song_title, artist):
    try:
        url = f"https://itunes.apple.com/search?term={artist} {song_title}&media=music"
        logging.debug(f"Fetching audio preview from iTunes API: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['results'][0].get('previewUrl')
    except Exception as e:
        logging.error(f"Error fetching audio preview: {e}")
        return None

# Generate Lyric Image
def generate_lyric_image(song_title, artist):
    try:
        img = Image.new("RGB", (1280, 720), color="white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        draw.text((100, 100), f"{song_title}\nby {artist}", fill="black", font=font)
        img.save(IMAGE_OUTPUT)
        logging.info(f"Lyric image saved: {IMAGE_OUTPUT}")
        return IMAGE_OUTPUT
    except Exception as e:
        logging.error(f"Error generating lyric image: {e}")
        return None

# Create Video with Audio Hook
def process_audio(audio_path, target_duration=30):
    try:
        audio_clip = AudioFileClip(audio_path)
        if audio_clip.duration > target_duration:
            audio_clip = audio_clip.subclipped(0, target_duration)
        else:
            loops = int(target_duration // audio_clip.duration) + 1
            audio_clips = [audio_clip] * loops
            audio_clip = concatenate_audioclips(audio_clips).subclipped(0, target_duration)
        return audio_clip
    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        return None

def create_video(image_path, audio_path, output_path, duration=30):
    try:
        image_clip = ImageClip(image_path).set_duration(duration).resize(height=720, width=1280)
        audio_clip = process_audio(audio_path, duration)
        video_clip = image_clip.set_audio(audio_clip)
        video_clip.write_videofile(output_path, codec="libx264", fps=24)
        logging.info(f"Video created successfully at 1280x720 resolution.")
        return output_path
    except Exception as e:
        logging.error(f"Error creating video: {e}")
        return None

# Tweet Video
def tweet_video(song_title, artist):
    try:
        m1 = api.media_upload(VIDEO_OUTPUT, media_category='tweet_video')
        media_id = m1.media_id_string
        logging.info(f"Video uploaded successfully. Media ID: {media_id}")
        tweet_text = f"🎵 {song_title} by {artist}\n#Trending #Music #NowPlaying"
        response = client.create_tweet(text=tweet_text, media_ids=[media_id])
        tweet_id = response.data['id']
        logging.info(f"Video tweeted successfully: https://twitter.com/user/status/{tweet_id}")
    except Exception as e:
        logging.error(f"Error tweeting video: {e}")

# Main Execution
def main():
    while True:
        try:
            song_title, artist = fetch_trending_song()
            if not song_title or not artist:
                continue
            album_cover = fetch_album_cover(song_title, artist)
            audio_preview = fetch_audio_preview(song_title, artist)
            if not album_cover or not audio_preview:
                continue
            image_path = generate_lyric_image(song_title, artist)
            response = requests.get(audio_preview, timeout=10)
            with open(AUDIO_OUTPUT, "wb") as f:
                f.write(response.content)
            video_path = create_video(image_path, AUDIO_OUTPUT, VIDEO_OUTPUT)
            if video_path:
                tweet_video(song_title, artist)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        logging.info("Waiting 2 hours before the next tweet...")
        time.sleep(7200)

if __name__ == "__main__":
    main()
