import requests
import tweepy
import os
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import time
import re
import emoji

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
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# ✅ Authenticate Twitter API v1.1 (Media Uploads)
auth_v1 = tweepy.OAuth1UserHandler(
    API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)
api = tweepy.API(auth_v1)

# ✅ Authenticate Twitter API v2 (Tweet Creation)
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    bearer_token=BEARER_TOKEN
)

# ✅ Paths
IMAGE_OUTPUT = "mj_lyric_image.png"
AUDIO_OUTPUT = "mj_audio_preview.mp3"
VIDEO_OUTPUT = "mj_lyric_video.mp4"

# ✅ Background Colors
PASTEL_COLORS = ["#FFF8E1", "#FCE4EC", "#E8F5E9", "#E3F2FD", "#F3E5F5"]

# ------------------------------------------------
# ✅ Fetch Random Michael Jackson Song
# ------------------------------------------------
def fetch_random_mj_song():
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=Michael+Jackson&api_key={LASTFM_API_KEY}&format=json"
        response = requests.get(url)
        response.raise_for_status()
        tracks = response.json().get("toptracks", {}).get("track", [])
        random_track = random.choice(tracks)
        song_title = random_track.get("name", "Unknown Song")
        print(f"✅ Selected Song: {song_title}")
        return song_title
    except Exception as e:
        print(f"❌ Error fetching song: {e}")
        return None

# ------------------------------------------------
# ✅ Fetch Lyrics
# ------------------------------------------------
def fetch_lyrics(song_title, artist):
    try:
        response = requests.get(f"https://api.lyrics.ovh/v1/{artist}/{song_title}")
        response.raise_for_status()
        data = response.json()
        return data.get("lyrics", "Lyrics not found")
    except Exception as e:
        print(f"❌ Error fetching lyrics: {e}")
    return None

# ------------------------------------------------
# ✅ Fetch Album Cover
# ------------------------------------------------
def fetch_album_cover(song_title, artist):
    try:
        url = f"https://itunes.apple.com/search?term={artist} {song_title}&media=music"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['results'][0].get('artworkUrl100')
    except Exception as e:
        print(f"❌ Error fetching album cover: {e}")
    return None

# ------------------------------------------------
# ✅ Fetch Audio Preview
# ------------------------------------------------
def fetch_audio_preview(song_title, artist):
    try:
        url = f"https://itunes.apple.com/search?term={artist} {song_title}&media=music"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['results'][0].get('previewUrl')
    except Exception as e:
        print(f"❌ Error fetching audio preview: {e}")
    return None

# ------------------------------------------------
# ✅ Dynamic Font Adjustment
# ------------------------------------------------
def adjust_font_size(draw, text, max_width, max_height, font_path, start_size=55):
    font_size = start_size
    while font_size > 10:
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.multiline_textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        if text_width <= max_width and text_height <= max_height:
            return font
        font_size -= 2
    return ImageFont.truetype(font_path, 10)

# ------------------------------------------------
# ✅ Generate Lyric Image
# ------------------------------------------------
def generate_lyric_image(song_title, artist, lyrics, album_cover_url):
    try:
        lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
        selected_lyrics = '\n'.join(random.sample(lines, min(len(lines), 2)))

        img = Image.new("RGB", (1200, 675), color=random.choice(PASTEL_COLORS))
        draw = ImageDraw.Draw(img)

        title_font = adjust_font_size(draw, song_title, 800, 60, "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf", 45)
        artist_font = adjust_font_size(draw, artist, 800, 40, "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf", 30)
        lyrics_font = adjust_font_size(draw, selected_lyrics, 1000, 400, "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf", 70)

        draw.text((50, 50), song_title, font=title_font, fill="black")
        draw.text((50, 120), artist, font=artist_font, fill="grey")
        draw.multiline_text((600, 350), selected_lyrics, font=lyrics_font, fill="black", anchor="mm", align="center")

        if album_cover_url and isinstance(album_cover_url, str):
            response = requests.get(album_cover_url)
            album_cover = Image.open(BytesIO(response.content)).resize((150, 150))
            img.paste(album_cover, (50, 500))

        draw.text((1050, 630), "@lyric_loops", font=ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf", 25), fill="black")
        img.save(IMAGE_OUTPUT, format="PNG")
        print("✅ Image saved successfully.")
        return IMAGE_OUTPUT, selected_lyrics
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        return None, None

# ------------------------------------------------
# ✅ Process Audio
# ------------------------------------------------
def process_audio(audio_path, target_duration=15):
    audio_clip = AudioFileClip(audio_path)
    if audio_clip.duration > target_duration:
        audio_clip = audio_clip.subclipped(0, target_duration)
    else:
        loops = int(target_duration // audio_clip.duration) + 1
        audio_clips = [audio_clip] * loops
        audio_clip = concatenate_audioclips(audio_clips).subclipped(0, target_duration)
    return audio_clip

# ------------------------------------------------
# ✅ Create Image Clip
# ------------------------------------------------
def create_image_clip(image_path, duration=15):
    image_clip = ImageClip(image_path).with_duration(duration)
    return image_clip

# ------------------------------------------------
# ✅ Create Video
# ------------------------------------------------
def create_video(image_path, audio_path, output_path, duration=15):
    try:
        # Create image and audio clips
        image_clip = create_image_clip(image_path, duration)
        audio_clip = process_audio(audio_path, duration)
        
        # Combine image and audio into a video clip
        video_clip = image_clip.with_audio(audio_clip)
        
        # Resize the video to 1280x720
        video_clip = video_clip.resized((1280, 720))
        
        # Write the video file
        video_clip.write_videofile(output_path, codec="libx264", fps=24)
        print("✅ Video created successfully at 1280x720 resolution.")
    except Exception as e:
        print(f"❌ Error generating video: {e}")

def sanitize_hashtag(text):
    """Sanitize text to be hashtag-friendly (no spaces or special characters)."""
    return re.sub(r'[^a-zA-Z0-9]', '', text.replace(' ', ''))

# ------------------------------------------------
# ✅ Tweet Video
# ------------------------------------------------
def tweet_video(song_title, artist):
    """Creates a tweet with the uploaded video using API v2 with rate limit handling."""
    try:
        # Step 1: Upload Video via API v1.1
        m1 = api.media_upload(
            VIDEO_OUTPUT,
            media_category='tweet_video'
        )
        
        # Ensure media_id is correctly extracted
        media_id = m1.media_id_string  # Ensures it's a string
        print(f"✅ Video uploaded successfully. Media ID: {media_id}")
        
        # Step 2: Check Media Processing
        processing_info = getattr(m1, 'processing_info', None)
        if processing_info:
            state = processing_info.get('state')
            while state != "succeeded":
                if state == "failed":
                    raise Exception("❌ Media processing failed.")
                wait_time = processing_info.get('check_after_secs', 5)
                print(f"⏳ Media still processing. Waiting {wait_time} seconds...")
                time.sleep(wait_time)

                # Re-check processing info
                status = api.get_status(m1.media_id)
                processing_info = getattr(status, 'processing_info', None)
                state = processing_info.get('state') if processing_info else "succeeded"

        print("✅ Media processing completed successfully.")
        
        # Step 3: Prepare Tweet Content
        artist_hashtag = f"#{sanitize_hashtag(artist)}"
        tweet_text = f"🎵 {song_title} by {artist}\n#Trending #Music {artist_hashtag}"
        
        # Step 4: Handle Rate Limit with Retry Logic
        max_retries = 5
        retry_delay = 60  # Start with a 60-second delay
        
        for attempt in range(max_retries):
            try:
                # ✅ Attempt to create a tweet with media
                response = client.create_tweet(
                    text=tweet_text,
                    media_ids=[media_id]  # Correct usage in API v2
                )
                
                tweet_id = response.data['id']
                print(f"✅ Video tweeted successfully: https://twitter.com/user/status/{tweet_id}")
                break  # Exit loop on success
            
            except tweepy.errors.TooManyRequests as e:
                reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + retry_delay))
                wait_time = max(reset_time - time.time(), retry_delay)
                print(f"⚠️ Rate limit exceeded. Retrying in {int(wait_time)} seconds...")
                time.sleep(wait_time)
            
            except tweepy.errors.BadRequest as e:
                print(f"❌ Bad Request: {e.response.text}")
                break  # Exit on incorrect request
            
            except tweepy.errors.TweepyException as e:
                print(f"❌ Tweepy error tweeting video: {e}")
                break  # Exit on other Tweepy exceptions
            
            except Exception as e:
                print(f"❌ Unexpected error tweeting video: {e}")
                break  # Exit on unexpected errors
    
    except tweepy.errors.TweepyException as e:
        print(f"❌ Tweepy error tweeting video: {e}")
    except Exception as e:
        print(f"❌ Unexpected error tweeting video: {e}")

# ------------------------------------------------
# ✅ Main Execution
# ------------------------------------------------
if __name__ == "__main__":
    song_title = fetch_random_mj_song()
    if song_title:
        artist = "Michael Jackson"
        lyrics = fetch_lyrics(song_title, artist)
        if lyrics:
            album_cover_url = fetch_album_cover(song_title, artist)
            image_path, selected_lyrics = generate_lyric_image(song_title, artist, lyrics, album_cover_url)
            if image_path:
                audio_preview_url = fetch_audio_preview(song_title, artist)
                if audio_preview_url:
                    # Download the audio preview
                    response = requests.get(audio_preview_url)
                    with open(AUDIO_OUTPUT, 'wb') as f:
                        f.write(response.content)

                    create_video(image_path, AUDIO_OUTPUT, VIDEO_OUTPUT)
                    tweet_video(song_title, artist)
