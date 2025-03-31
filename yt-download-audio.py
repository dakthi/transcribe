import yt_dlp

url = "https://www.youtube.com/watch?v=HPB-I7yWh5U"
ydl_opts = {
    "format": "bestaudio",  # Download the best audio available
    "outtmpl": "%(title)s.%(ext)s",  # Keep the title as the filename
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",  # Convert to MP3 (change to 'wav' if needed)
        "preferredquality": "192",  # Set bitrate (e.g., 192kbps for MP3)
    }]
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
