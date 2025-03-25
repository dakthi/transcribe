import os
import whisper
import torch
import pandas as pd
import logging
import time
import pyaudio
import wave
import numpy as np
import queue
import threading

# Configure logging
logging.basicConfig(
    filename="transcription.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",  # Overwrites the log file on each run
)

# Define paths
MASTER_FOLDER = os.path.expanduser("~/Downloads/Organized/Folders/Folders/python-transcribe")
CSV_FILE = os.path.join(MASTER_FOLDER, "transcription.csv")

# Load Whisper model with FP32 enforcement
MODEL_NAME = "base"  # Choose "tiny", "base", "small", "medium", "large", "turbo"
model = whisper.load_model(MODEL_NAME).to(torch.float32)  # 🔥 Force FP32

# Audio settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
RECORD_SECONDS = 5  # Segment length in seconds

# Ensure output directory exists
os.makedirs(MASTER_FOLDER, exist_ok=True)

def ensure_csv_exists():
    """Create CSV file with headers if it doesn't exist."""
    if not os.path.exists(CSV_FILE):
        logging.info("CSV file not found. Creating a new one.")
        df = pd.DataFrame(columns=["Filename", "Transcription"])
        df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def update_csv(transcription):
    """Update CSV file with the transcription in real-time."""
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    base_filename = f"mic_transcription_{timestamp}.wav"
    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        logging.error(f"[ERROR] Reading CSV: {e}")
        df = pd.DataFrame(columns=["Filename", "Transcription"])

    new_row = pd.DataFrame([{"Filename": base_filename, "Transcription": transcription}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def record_audio(queue):
    """Records audio from the microphone and puts it in a queue."""
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    logging.info("[INFO] Recording started...")
    
    while True:
        frames = []
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        queue.put(frames)
    
    stream.stop_stream()
    stream.close()
    audio.terminate()

def transcribe_live():
    """Continuously records and transcribes audio in real-time."""
    audio_queue = queue.Queue()
    threading.Thread(target=record_audio, args=(audio_queue,), daemon=True).start()
    
    while True:
        frames = audio_queue.get()
        audio_data = b"".join(frames)
        np_audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        logging.info("[INFO] Transcribing...")
        result = model.transcribe(np_audio, fp16=False)
        transcription = result["text"].strip()
        
        if transcription:
            print(f"Live Transcription: {transcription}")
            update_csv(transcription)
            logging.info(f"[TRANSCRIBED] {transcription}")
        
        time.sleep(1)  # Prevent excessive CPU usage

def main():
    ensure_csv_exists()
    transcribe_live()

if __name__ == "__main__":
    main()
