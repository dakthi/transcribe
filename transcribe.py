import os
import whisper
import torch
import pandas as pd
import logging
import time
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    filename="transcription.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",  # Overwrites the log file on each run
)

# Define paths
MASTER_FOLDER = os.path.expanduser("~/Downloads/Folders/python-transcribe")
CSV_FILE = os.path.join(MASTER_FOLDER, "transcription.csv")

# Load Whisper model with FP32 enforcement
MODEL_NAME = "turbo"  # Choose "tiny", "base", "small", "medium", "large", "turbo"
model = whisper.load_model(MODEL_NAME).to(torch.float32)  # 🔥 Force FP32

def ensure_csv_exists():
    """Create CSV file with headers if it doesn't exist."""
    if not os.path.exists(CSV_FILE):
        logging.info("CSV file not found. Creating a new one.")
        df = pd.DataFrame(columns=["Filename", "Transcription"])
        df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def load_existing_transcriptions():
    """Load existing transcriptions from CSV to avoid re-processing files."""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if "Filename" in df:
            return set(df["Filename"].apply(os.path.basename).astype(str))
    return set()

def update_csv(filename, transcription):
    """Update CSV file with the transcription in real-time."""
    base_filename = os.path.basename(filename)
    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        logging.error(f"[ERROR] Reading CSV: {e}")
        df = pd.DataFrame(columns=["Filename", "Transcription"])

    if base_filename in df["Filename"].apply(os.path.basename).values:
        df.loc[df["Filename"].apply(os.path.basename) == base_filename, "Transcription"] = transcription
    else:
        new_row = pd.DataFrame([{"Filename": base_filename, "Transcription": transcription}])
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def transcribe_audio_local(file_path):
    """
    Transcribe audio using the local Whisper model.
    Uses tqdm progress bar in logs and updates CSV in real-time.
    """
    base_filename = os.path.basename(file_path)
    logging.info(f"\n[START] Transcribing: {base_filename}")

    try:
        # Load and preprocess audio
        audio = whisper.load_audio(file_path)
        audio = whisper.pad_or_trim(audio)

        # Convert to log-Mel spectrogram with FP32 enforcement
        mel = whisper.log_mel_spectrogram(audio).to(torch.float32).to(model.device)

        # Detect language
        result = model.transcribe(file_path, fp16=False)
        detected_lang = result["language"]
        logging.info(f"[INFO] Detected Language: {detected_lang}")

        total_segments = len(result["segments"])
        transcription = ""

        with tqdm(total=total_segments, desc=f"Processing {base_filename}", unit="segment") as pbar:
            for segment in result["segments"]:
                segment_text = segment["text"]
                transcription += " " + segment_text
                update_csv(base_filename, transcription.strip())  # Update CSV in real-time

                pbar.update(1)  # Update progress bar
                time.sleep(0.1)  # Small delay for better visibility in logs

        logging.info(f"\n[COMPLETED] {base_filename} - Transcription saved.")
        return transcription

    except Exception as e:
        logging.error(f"[ERROR] Transcribing {base_filename}: {e}")
        return None

def main():
    """Process and transcribe new audio files in the folder."""
    if not os.path.exists(MASTER_FOLDER):
        logging.error(f"[ERROR] Folder '{MASTER_FOLDER}' does not exist.")
        return

    ensure_csv_exists()
    existing_files = load_existing_transcriptions()

    for file in os.listdir(MASTER_FOLDER):
        if file.endswith((".mp3", ".wav", ".m4a")):
            if file in existing_files:
                logging.info(f"[SKIP] Already processed: {file}")
                continue

            file_path = os.path.join(MASTER_FOLDER, file)
            logging.info(f"[PROCESSING] {file}")

            transcript = transcribe_audio_local(file_path)

            if transcript:
                logging.info(f"[DONE] {file} - Transcription saved.")

if __name__ == "__main__":
    main()
