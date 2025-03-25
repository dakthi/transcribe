import os
import whisper
import torch
import pandas as pd
import logging
import time
import subprocess
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    filename="transcription.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
)

# Define paths
MASTER_FOLDER = os.path.expanduser("~/Downloads/Organized/Folders/Folders/python-transcribe")
CSV_FILE = os.path.join(MASTER_FOLDER, "transcription.csv")
SEGMENTS_FOLDER = os.path.join(MASTER_FOLDER, "segments")

# Ensure segments folder exists
os.makedirs(SEGMENTS_FOLDER, exist_ok=True)

# Load Whisper model with FP32
MODEL_NAME = "large-v3"
model = whisper.load_model(MODEL_NAME).to(torch.float32)

def ensure_csv_exists():
    """Create CSV file with headers if it doesn't exist."""
    if not os.path.exists(CSV_FILE):
        logging.info("CSV file not found. Creating a new one.")
        df = pd.DataFrame(columns=["Filename", "Transcription"])
        df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def clean_csv(df):
    """Drop any unnamed columns caused by prior indexing."""
    return df.loc[:, ~df.columns.str.contains("^Unnamed")]

def load_existing_transcriptions():
    """Load existing transcriptions to avoid re-processing."""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df = clean_csv(df)
        if "Filename" in df:
            return set(df["Filename"].apply(os.path.basename).astype(str))
    return set()

def update_csv(filename, transcription):
    """Update the CSV with new or updated transcription."""
    base_filename = os.path.basename(filename)
    try:
        df = pd.read_csv(CSV_FILE)
        df = clean_csv(df)
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
    """Transcribe audio file with Whisper using segmentation and word-level control."""
    base_filename = os.path.basename(file_path)
    logging.info(f"[START] Transcribing: {base_filename}")
    transcription = ""

    try:
        file_segments_dir = os.path.join(SEGMENTS_FOLDER, os.path.splitext(base_filename)[0])
        os.makedirs(file_segments_dir, exist_ok=True)

        output_pattern = os.path.join(file_segments_dir, f"{base_filename}_%03d.wav")

        cmd = [
            "ffmpeg", "-i", file_path,
            "-f", "segment", "-segment_time", "30",
            "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
            output_pattern
        ]
        subprocess.run(cmd, check=True)

        segment_files = sorted(
            [os.path.join(file_segments_dir, f) for f in os.listdir(file_segments_dir) if f.endswith(".wav")]
        )

        if not segment_files:
            logging.error(f"[ERROR] No segments created for {base_filename}.")
            return None

        lang_result = model.transcribe(segment_files[0], fp16=False)
        detected_lang = lang_result["language"]
        logging.info(f"[INFO] Detected Language: {detected_lang}")

        with tqdm(total=len(segment_files), desc=f"Processing {base_filename}", unit="segment") as pbar:
            for seg in segment_files:
                result = model.transcribe(
                    seg,
                    fp16=False,
                    word_timestamps=True,
                    language=detected_lang,
                    hallucination_silence_threshold=2.0  # Skip silent segments that might be hallucinated
                )

                transcription += " " + result["text"]
                update_csv(base_filename, transcription.strip())
                pbar.update(1)
                time.sleep(0.1)

        logging.info(f"[COMPLETED] {base_filename} - Transcription saved.")
        return transcription

    except Exception as e:
        logging.error(f"[ERROR] Transcribing {base_filename}: {e}")
        return None

def main():
    if not os.path.exists(MASTER_FOLDER):
        logging.error(f"[ERROR] Folder '{MASTER_FOLDER}' does not exist.")
        return

    ensure_csv_exists()
    existing_files = load_existing_transcriptions()

    for file in os.listdir(MASTER_FOLDER):
        if file.endswith((".mp3", ".wav", ".m4a", ".WAV", ".MP3")):
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
