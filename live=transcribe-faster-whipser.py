import os
import time
import queue
import threading
import logging
import wave
import pyaudio
import numpy as np
import pandas as pd
import soundfile as sf
import subprocess
import re
import sys
from faster_whisper import WhisperModel

# ------------------ CONFIGURATION ------------------
MASTER_FOLDER = os.path.expanduser("~/Downloads/Organized/Folders/Folders/python-transcribe")
CSV_FILE = os.path.join(MASTER_FOLDER, "transcription.csv")
MODEL_NAME = "turbo"

RECORD_SECONDS = 10
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

os.makedirs(MASTER_FOLDER, exist_ok=True)

logging.basicConfig(
    filename="transcription.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
)

model = WhisperModel(
    MODEL_NAME,
    device="cpu",
    compute_type="int8"
)

def ensure_csv_exists():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=["Filename", "Transcription"])
        df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def save_wav_file(filename, frames):
    path = os.path.join(MASTER_FOLDER, filename)
    wf = wave.open(path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def denoise_audio(input_path, output_path):
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-af", "afftdn",
            output_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg denoise failed: {e}")

def record_audio(q):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    logging.info("Recording started...")
    try:
        while True:
            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            q.put(frames)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

def transcribe_live():
    ensure_csv_exists()
    audio_queue = queue.Queue()
    all_frames = []
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    raw_filename = f"mic_transcription_{timestamp}.wav"
    cleaned_filename = raw_filename.replace(".wav", "_cleaned.wav")

    threading.Thread(target=record_audio, args=(audio_queue,), daemon=True).start()

    print("\n🎙️ Recording in 10-second chunks. Press Ctrl+C to stop...\n")
    try:
        while True:
            frames = audio_queue.get()
            all_frames.extend(frames)

            # Transcribe chunk for live logging
            audio_data = b"".join(frames)
            np_audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(np_audio, beam_size=5)
            chunk_text = "".join([segment.text for segment in segments]).strip()
            if chunk_text:
                print(f"📝 Live chunk: {chunk_text}")
                logging.info(f"Live chunk: {chunk_text}")

    except KeyboardInterrupt:
        print("\n🔁 Processing final audio...")

        if len(all_frames) == 0:
            print("ℹ️ No speech was recorded.")
            return

        save_wav_file(raw_filename, all_frames)
        raw_path = os.path.join(MASTER_FOLDER, raw_filename)

        cleaned_path = os.path.join(MASTER_FOLDER, cleaned_filename)
        denoise_audio(raw_path, cleaned_path)

        audio_data, sr = sf.read(cleaned_path)
        audio_data = audio_data.astype(np.float32)
        segments, _ = model.transcribe(audio_data, beam_size=5)
        final_text = "".join([segment.text for segment in segments]).strip()

        if final_text:
            df = pd.read_csv(CSV_FILE)
            new_row = pd.DataFrame([{"Filename": cleaned_filename, "Transcription": final_text}])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
            print(f"✅ Transcription saved to CSV as: {cleaned_filename}")
            print(f"\n📄 Full transcription:\n{final_text}\n")
        else:
            print("ℹ️ No speech was detected in the final audio.")

def main():
    transcribe_live()

if __name__ == "__main__":
    main()