import requests
import tweepy
import os
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import random

# ✅ Load Environment Variables
load_dotenv()

# ✅ API Credentials
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# ✅ Authenticate with Twitter API v2 (OAuth2)
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# ✅ Authenticate with Tweepy v1.1 for Media Uploads
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

# ✅ Output image path
IMAGE_OUTPUT = "lyric_image.png"

# ✅ Soft Pastel Background Colors
PASTEL_COLORS = [
    "#FFF8E1", "#FCE4EC", "#E8F5E9", "#E3F2FD", "#F3E5F5",
    "#D1C4E9", "#FFECB3", "#FFCCBC", "#CFD8DC"
]

# ------------------------------------------------
# ✅ Fetch Random Song from Last.fm
# ------------------------------------------------
def fetch_random_song_from_lastfm():
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=chart.gettoptracks&api_key={LASTFM_API_KEY}&format=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        tracks = data.get("tracks", {}).get("track", [])
        
        if not tracks:
            print("❌ No tracks found.")
            return None, None
        
        random_track = random.choice(tracks)
        song_title = random_track.get("name", "Unknown Song")
        artist = random_track.get("artist", {}).get("name", "Unknown Artist")
        print(f"✅ Selected Song: {song_title} by {artist}")
        return song_title, artist
    except Exception as e:
        print(f"❌ Error fetching song: {e}")
        return None, None

# ------------------------------------------------
# ✅ Fetch Lyrics
# ------------------------------------------------
def fetch_lyrics(song_title, artist):
    sources = [
        f"https://api.lyrics.ovh/v1/{artist}/{song_title}",
        f"http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect?artist={artist}&song={song_title}",
        f"http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={LASTFM_API_KEY}&artist={artist}&track={song_title}&format=json"
    ]
    
    for source in sources:
        try:
            response = requests.get(source)
            response.raise_for_status()
            data = response.json()
            lyrics = data.get("lyrics") or data.get("track", {}).get("wiki", {}).get("summary")
            if lyrics:
                print("✅ Lyrics fetched successfully.")
                return lyrics
        except Exception as e:
            print(f"❌ Error fetching lyrics from {source}: {e}")
    print("❌ All lyric sources failed.")
    return None

# ------------------------------------------------
# ✅ Fetch Album Cover
# ------------------------------------------------
def fetch_album_cover(song_title, artist):
    sources = [
        f"https://itunes.apple.com/search?term={artist} {song_title}&media=music",
        f"https://api.deezer.com/search?q={artist} {song_title}",
        f"http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={LASTFM_API_KEY}&artist={artist}&track={song_title}&format=json"
    ]
    
    for source in sources:
        try:
            response = requests.get(source)
            response.raise_for_status()
            data = response.json()
            if "results" in data and data["results"]:
                return data["results"][0].get("artworkUrl100")
            if "data" in data and data["data"]:
                return data["data"][0].get("album", {}).get("cover_big")
            if "track" in data:
                return data["track"].get("album", {}).get("image", [{}])[-1].get("#text")
        except Exception as e:
            print(f"❌ Error fetching album cover from {source}: {e}")
    print("❌ All album cover sources failed.")
    return None

def adjust_font_size(draw, text, max_width, max_height, font_path, start_size=55):
    """
    Dynamically adjusts the font size to fit the text within given dimensions.
    
    Args:
        draw: PIL.ImageDraw instance.
        text: The text string to fit.
        max_width: Maximum width allowed for the text.
        max_height: Maximum height allowed for the text.
        font_path: Path to the font file.
        start_size: Starting font size to test fitting.
    
    Returns:
        PIL.ImageFont instance with adjusted size.
    """
    font_size = start_size
    while font_size > 10:  # Prevent font size from getting too small
        font = ImageFont.truetype(font_path, font_size)
        
        # Calculate the bounding box of the text
        text_bbox = draw.multiline_textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Check if the text fits within the allowed dimensions
        if text_width <= max_width and text_height <= max_height:
            return font
        
        font_size -= 2  # Decrease font size incrementally if it doesn't fit
    
    # Return minimum size if no fitting size is found
    return ImageFont.truetype(font_path, 10)


# ------------------------------------------------
# ✅ Generate Lyric Image
# ------------------------------------------------
def generate_lyric_image(song_title, artist, lyrics, album_cover_url):
    try:
        # Split the lyrics into lines and select two random lines
        lines = lyrics.split('\n')
        if len(lines) >= 2:
            selected_lyrics = '\n'.join(random.sample(lines, 2))  # Randomly select two lines
        else:
            selected_lyrics = '\n'.join(lines)  # If there are fewer than two lines, use all available

        img = Image.new("RGB", (1200, 675), color=random.choice(PASTEL_COLORS))
        draw = ImageDraw.Draw(img)

        title_font = adjust_font_size(draw, song_title, 800, 60, "arialbd.ttf", 45)
        artist_font = adjust_font_size(draw, artist, 800, 40, "arial.ttf", 30)
        lyrics_font = adjust_font_size(draw, selected_lyrics, 1000, 400, "arialbd.ttf", 70)

        draw.text((50, 50), song_title, font=title_font, fill="black")
        draw.text((50, 120), artist, font=artist_font, fill="grey")
        draw.multiline_text((600, 350), selected_lyrics, font=lyrics_font, fill="black", anchor="mm", align="center")

        if album_cover_url:
            response = requests.get(album_cover_url)
            album_cover = Image.open(BytesIO(response.content)).resize((150, 150))
            img.paste(album_cover, (50, 500))

        draw.text((1050, 630), "@lyric_loops", font=ImageFont.truetype("arial.ttf", 25), fill="black")
        img.save(IMAGE_OUTPUT, format="PNG")
        print("✅ Image saved successfully.")
        return IMAGE_OUTPUT
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        return None

# ------------------------------------------------
# ✅ Post on Twitter
# ------------------------------------------------
def post_lyric_image(image_path, song_title, artist, lyrics):
    tweet_text = f"🎵 {lyrics[:200]}... - {artist}"
    media = api.media_upload(image_path)
    client.create_tweet(text=tweet_text, media_ids=[media.media_id_string])
    print("✅ Tweet posted successfully.")

# ------------------------------------------------
# ✅ Main
# ------------------------------------------------
if __name__ == "__main__":
    song_title, artist = fetch_random_song_from_lastfm()
    lyrics = fetch_lyrics(song_title, artist)
    cover_url = fetch_album_cover(song_title, artist)
    if lyrics:
        image = generate_lyric_image(song_title, artist, lyrics, cover_url)
        if image:
            post_lyric_image(image, song_title, artist, lyrics)
