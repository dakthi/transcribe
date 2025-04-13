import yt_dlp

url = "https://www.youtube.com/watch?v=ZhCBEfLwEr4"
ydl_opts = {
    "format": "best",
    "outtmpl": "%(title)s.%(ext)s"
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
