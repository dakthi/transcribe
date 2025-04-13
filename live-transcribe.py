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
import pyperclip
from pynput import keyboard as pynput_keyboard
from faster_whisper import WhisperModel

# ------------------ CONFIGURATION ------------------
SHOULD_SAVE_AUDIO = False
SHOULD_CLEAN_AUDIO = False if SHOULD_SAVE_AUDIO else False
CLIPBOARD_ENABLED = True
MASTER_FOLDER = os.path.expanduser("/Users/dakthi/Downloads/make a new folder'")
CSV_FILE = os.path.join(MASTER_FOLDER, "transcription.csv")
MODEL_NAME = "medium"

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

# 🧠 Event to signal clipboard + memory reset
reset_event = threading.Event()

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

def listen_for_reset_clipboard():
    COMBO = {pynput_keyboard.Key.cmd, pynput_keyboard.Key.shift, pynput_keyboard.KeyCode(char='x')}
    current_keys = set()

    def on_press(key):
        current_keys.add(key)
        if all(k in current_keys for k in COMBO):
            pyperclip.copy("")
            reset_event.set()
            print("🧹 Manual clipboard + memory reset triggered (Cmd+Shift+X).")
            current_keys.clear()

    def on_release(key):
        if key in current_keys:
            current_keys.remove(key)

    listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

def transcribe_live():
    ensure_csv_exists()
    audio_queue = queue.Queue()
    all_frames = []
    full_transcription = ""
    clipboard_memory = ""
    timestamp = time.strftime("%y%m%d_%H%M%S")
    raw_filename = f"{timestamp}.wav"
    cleaned_filename = raw_filename.replace(".wav", "_cleaned.wav")

    threading.Thread(target=record_audio, args=(audio_queue,), daemon=True).start()
    threading.Thread(target=listen_for_reset_clipboard, daemon=True).start()

    print("\n🎙️ Recording in 10-second chunks. Press Ctrl+C to stop...")
    print("📋 Press Cmd+Shift+X to clear the clipboard + reset memory.\n")

    try:
        while True:
            frames = audio_queue.get()
            all_frames.extend(frames)

            # 🧠 Reset clipboard memory if triggered
            if reset_event.is_set():
                clipboard_memory = ""
                reset_event.clear()

            # Transcribe chunk
            audio_data = b"".join(frames)
            np_audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(np_audio, beam_size=5)
            chunk_text = "".join([segment.text for segment in segments]).strip()

            if chunk_text:
                print(f"{chunk_text}")
                logging.info(f"{chunk_text}")

                # Append and update cumulative transcription in CSV
                full_transcription += " " + chunk_text
                df = pd.read_csv(CSV_FILE) if os.path.exists(CSV_FILE) else pd.DataFrame(columns=["Filename", "Transcription"])

                if raw_filename in df["Filename"].values:
                    df.loc[df["Filename"] == raw_filename, "Transcription"] = full_transcription.strip()
                else:
                    new_row = pd.DataFrame([{"Filename": raw_filename, "Transcription": full_transcription.strip()}])
                    df = pd.concat([df, new_row], ignore_index=True)

                df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

                # 📋 Clipboard handling
                if CLIPBOARD_ENABLED:
                    clipboard_memory += " " + chunk_text
                    pyperclip.copy(clipboard_memory.strip())

    except KeyboardInterrupt:
        print("\n🔁 Finalising...")

        if len(all_frames) == 0:
            print("ℹ️ No speech was recorded.")
            return

        if SHOULD_SAVE_AUDIO:
            save_wav_file(raw_filename, all_frames)
            raw_path = os.path.join(MASTER_FOLDER, raw_filename)

            if SHOULD_CLEAN_AUDIO:
                cleaned_path = os.path.join(MASTER_FOLDER, cleaned_filename)
                denoise_audio(raw_path, cleaned_path)
                print(f"✅ Cleaned audio saved as: {cleaned_filename}")
            else:
                print(f"✅ Audio saved as: {raw_filename}")
        else:
            print("✅ Transcription was saved during live processing. Audio not saved.")

        if CLIPBOARD_ENABLED:
            pyperclip.copy("")
            print("🧹 Clipboard cleared.")

def main():
    transcribe_live()

if __name__ == "__main__":
    main()
