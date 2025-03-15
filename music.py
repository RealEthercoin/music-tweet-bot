import requests
import tweepy
import os
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
import time
import lyricsgenius
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

# Load Environment Variables
load_dotenv()

# API Credentials
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")

# Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, 
                                                            client_secret=SPOTIFY_CLIENT_SECRET))

# Initialize Genius API with higher timeout
genius = lyricsgenius.Genius(GENIUS_API_TOKEN, timeout=10)

# Authenticate Twitter API v1.1 (Media Uploads)
auth_v1 = tweepy.OAuth1UserHandler(
    API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)
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
IMAGE_OUTPUT = "lyric_image.png"
AUDIO_OUTPUT = "hook_trimmed.mp3"
VIDEO_OUTPUT = "lyric_video.mp4"

# Constants for video dimensions
VIDEO_SIZE = (1280, 720)

def fetch_mj_song():
    try:
        # Search for Michael Jackson's tracks using Spotify
        results = sp.search(q='artist:Michael Jackson', type='track', limit=50)
        if not results['tracks']['items']:
            raise Exception("No tracks found for Michael Jackson.")
        
        # Randomly pick a song
        random_track = random.choice(results['tracks']['items'])
        song_title = random_track['name']
        print(f"Selected Song: {song_title} by Michael Jackson")
        return song_title
    except Exception as e:
        print(f"Error fetching song: {e}")
        return None

def fetch_lyrics(song_title, artist):
    # Try Genius API first
    try:
        song = genius.search_song(song_title, artist)
        if song and song.lyrics:
            # Clean up the lyrics
            lyrics = clean_lyrics(song.lyrics)
            print("Lyrics fetched from Genius API.")
            return lyrics
        else:
            raise Exception("Genius API did not return lyrics.")
    except Exception as e:
        print(f"Error fetching lyrics from Genius API: {e}")
        print("Trying Lyrics.ovh API...")
    
    # Fallback to Lyrics.ovh API
    try:
        sanitized_artist = artist.replace(' ', '%20')
        url = f"https://api.lyrics.ovh/v1/{sanitized_artist}/{song_title}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "lyrics" in data and data["lyrics"].strip():
            # Clean up the lyrics
            lyrics = clean_lyrics(data["lyrics"])
            print("Lyrics fetched from Lyrics.ovh API.")
            return lyrics
        else:
            raise Exception("Lyrics.ovh API did not return lyrics.")
    except Exception as e:
        print(f"Error fetching lyrics from Lyrics.ovh API: {e}")
    
    print("Unable to fetch lyrics from any source.")
    return None

def clean_lyrics(lyrics):
    # Less aggressive cleaning, keep more context
    # Remove contributor information
    cleaned_lyrics = re.sub(r'^\d+\s+Contributors.*\n?', '', lyrics, flags=re.MULTILINE)
    # Remove text in square brackets but keep newlines
    cleaned_lyrics = re.sub(r'\[.*?\]', '', cleaned_lyrics)
    # Remove any lines that contain 'Lyrics' or similar metadata
    cleaned_lyrics = re.sub(r'^.*Lyrics.*\n?', '', cleaned_lyrics, flags=re.MULTILINE)
    # Remove extra newlines but keep single newlines for structure
    cleaned_lyrics = re.sub(r'\n\s*\n', '\n', cleaned_lyrics)
    # Remove leading/trailing whitespace
    cleaned_lyrics = cleaned_lyrics.strip()
    
    # Split into lines
    lines = [line.strip() for line in cleaned_lyrics.split('\n') if line.strip()]
    total_lines = len(lines)
    
    # Ensure we select at least 3 lines, even if we need to adjust our criteria
    if total_lines >= 3:
        # Randomly choose a starting point ensuring we can select 3 consecutive lines
        start_index = random.randint(0, total_lines - 3)
        # Select 3 consecutive lines from this starting point
        selected_lyrics = ' '.join(lines[start_index:start_index + 3])
    else:
        # If there are fewer than 3 lines, join all available lines
        selected_lyrics = ' '.join(lines)
        # If this still results in an empty string, raise an error
        if not selected_lyrics.strip():
            raise ValueError("Not enough valid lyric lines to display after cleaning.")
    
    return selected_lyrics

def fetch_album_cover(song_title, artist):
    try:
        # Use iTunes API for album cover
        url = f"https://itunes.apple.com/search?term={artist}+{song_title}&media=music&limit=1"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['resultCount'] > 0:
            return data['results'][0]['artworkUrl100']
        else:
            raise Exception("Album cover not found.")
    except Exception as e:
        print(f"Error fetching album cover: {e}")
    return None

def fetch_audio_preview(song_title, artist):
    try:
        # Use iTunes API for audio preview
        url = f"https://itunes.apple.com/search?term={artist}+{song_title}&media=music&limit=1"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['resultCount'] > 0:
            return data['results'][0]['previewUrl']
        else:
            raise Exception("Audio preview not found.")
    except Exception as e:
        print(f"Error fetching audio preview: {e}")
    return None

def generate_lyric_image(song_title, artist, lyrics, album_cover_url=None):
    try:
        # Clean the lyrics before processing
        cleaned_lyrics = clean_lyrics(lyrics)
        
        # Create image with black background for video size
        img = Image.new("RGB", VIDEO_SIZE, color="black")
        draw = ImageDraw.Draw(img)

        # Load Fonts
        title_font = ImageFont.truetype("Roboto-Bold.ttf", 80)
        artist_font = ImageFont.truetype("Roboto-Regular.ttf", 60)
        lyrics_font = ImageFont.truetype("Roboto-Bold.ttf", 70)
        branding_font = ImageFont.truetype("Roboto-Italic.ttf", 40)

        # Positioning for 720p aspect ratio
        draw.text((640, 50), song_title, font=title_font, fill="white", anchor="mm", align="center")
        draw.text((640, 150), artist, font=artist_font, fill="grey", anchor="mm", align="center")

        def wrap_text(text, font, max_width):
            """Word wrapping."""
            lines = []
            words = text.split()
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if draw.textlength(test_line, font=font) <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            return '\n'.join(lines)

        # Wrap the lyrics to fit within the image dimensions
        wrapped_lyrics = wrap_text(cleaned_lyrics, lyrics_font, 1100)
        draw.multiline_text((640, 350), wrapped_lyrics, font=lyrics_font, fill="white", anchor="mm", align="center")

        draw.text((1110, 640), "@hourlykingofpop", font=branding_font, fill="white", anchor="mm")
        if album_cover_url:
            response = requests.get(album_cover_url)
            album_cover = Image.open(BytesIO(response.content)).resize((150, 150))
            img.paste(album_cover, (50, 550))
        img.save(IMAGE_OUTPUT)
        return IMAGE_OUTPUT
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def create_video(image_path, audio_path, output_path, duration=15):
    try:
        image_clip = ImageClip(image_path).with_duration(duration).resized(VIDEO_SIZE)
        audio_clip = AudioFileClip(audio_path).subclipped(0, min(duration, 140))
        video = image_clip.with_audio(audio_clip)

        video.write_videofile(output_path, 
                              codec="libx264", 
                              audio_codec="aac", 
                              fps=30, 
                              bitrate="5000k")
        
        print("Video created successfully.")
    except Exception as e:
        print(f"Error creating video: {e}")
        return False
    return True

def tweet_video(song_title, artist):
    try:
        m1 = api.media_upload(
            VIDEO_OUTPUT,
            media_category='tweet_video'
        )
        media_id = m1.media_id_string
        print(f"Video uploaded successfully. Media ID: {media_id}")

        processing_info = getattr(m1, 'processing_info', None)
        if processing_info:
            state = processing_info.get('state')
            while state != "succeeded":
                if state == "failed":
                    raise Exception("Media processing failed.")
                wait_time = processing_info.get('check_after_secs', 5)
                print(f"Media still processing. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                status = api.get_status(m1.media_id)
                processing_info = getattr(status, 'processing_info', None)
                state = processing_info.get('state') if processing_info else "succeeded"

        print("Media processing completed successfully.")
        
        tweet_text = f"{song_title} by {artist}\n#MJ #Kingofpop"
        
        max_retries = 5
        retry_delay = 60
        
        for attempt in range(max_retries):
            try:
                response = client.create_tweet(
                    text=tweet_text,
                    media_ids=[media_id]
                )
                tweet_id = response.data['id']
                print(f"Video tweeted successfully: https://twitter.com/user/status/{tweet_id}")
                return True
            except tweepy.errors.TooManyRequests as e:
                reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + retry_delay))
                wait_time = max(reset_time - time.time(), retry_delay)
                print(f"Rate limit exceeded. Retrying in {int(wait_time)} seconds...")
                time.sleep(wait_time)
            except Exception as e:
                print(f"Error tweeting video: {e}")
                if attempt == max_retries - 1:  # Last attempt
                    return False
    except Exception as e:
        print(f"Unexpected error tweeting video: {e}")
    return False

if __name__ == "__main__":
    artist = "Michael Jackson"
    song_title = fetch_mj_song()
    
    if song_title:
        lyrics = fetch_lyrics(song_title, artist)
        album_cover = fetch_album_cover(song_title, artist)
        audio_preview = fetch_audio_preview(song_title, artist)

        print(f"Album cover URL: {album_cover}")
        print(f"Audio preview URL: {audio_preview}")

        if lyrics and album_cover and audio_preview:
            try:
                # Generate Lyric Image
                image_path = generate_lyric_image(song_title, artist, lyrics, album_cover)
                if image_path:
                    # Download the audio preview
                    response = requests.get(audio_preview)
                    with open(AUDIO_OUTPUT, 'wb') as f:
                        f.write(response.content)
                    
                    # Create the video
                    if create_video(image_path, AUDIO_OUTPUT, VIDEO_OUTPUT):
                        # Post the video on Twitter
                        if not tweet_video(song_title, artist):
                            print("Failed to tweet video.")
                    else:
                        print("Failed to create video.")
                else:
                    print("Failed to generate image.")
            except Exception as e:
                print(f"An error occurred during execution: {e}")
        else:
            print("Missing necessary resources: lyrics, album cover, or audio preview.")
    else:
        print("No song title obtained.")
