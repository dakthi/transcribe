import re
import os
import pandas as pd
import logging
import time
import subprocess
from tqdm import tqdm
from faster_whisper import WhisperModel

def clean_hallucinations(text):
    """
    Loại bỏ những cụm không mong muốn trong transcript
    """
    # Các cụm thường gặp để loại bỏ
    patterns = [
        r"Hãy subscribe cho kênh.*?(?:video hấp dẫn|để không bỏ lỡ|La La School).*?",  # loại bỏ cả cụm
        r"Ghiền Mì Gõ",
        r"Cảm ơn các bạn đã theo dõi và hẹn gặp lại.",
        r"La La School", 
        r"để không bỏ lỡ.*?video hấp dẫn",
        r"những video hấp dẫn",
        r"hã",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Dọn whitespace dư thừa
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

# Configure logging
logging.basicConfig(
    filename="transcription.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
)

# Define paths
MASTER_FOLDER = os.path.expanduser("/Users/dakthi/Downloads/Organized/Folders/Folders/python-transcribe")
CSV_FILE = os.path.join(MASTER_FOLDER, "transcription.csv")
SEGMENTS_FOLDER = os.path.join(MASTER_FOLDER, "segments")

# Ensure segments folder exists
os.makedirs(SEGMENTS_FOLDER, exist_ok=True)

# Load Faster-Whisper model
MODEL_NAME = "medium"  # Hoặc "small", "base", v.v.
model = WhisperModel(MODEL_NAME, compute_type="int8")

def ensure_csv_exists():
    """
    Tạo file CSV nếu chưa có
    """
    if not os.path.exists(CSV_FILE):
        logging.info("CSV file not found. Creating a new one.")
        df = pd.DataFrame(columns=["Filename", "Transcription"])
        df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def clean_csv(df):
    """
    Xoá các cột Unnamed (nếu có) trong DataFrame
    """
    return df.loc[:, ~df.columns.str.contains("^Unnamed")]

def load_existing_transcriptions():
    """
    Lấy ra danh sách các filename đã được xử lý trong CSV
    """
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df = clean_csv(df)
        if "Filename" in df:
            return set(df["Filename"].apply(os.path.basename).astype(str))
    return set()

def update_csv(filename, transcription):
    """
    Cập nhật (hoặc thêm) bản ghi transcript vào CSV
    """
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
    """
    Chia file âm thanh thành các segment 30 giây, 
    transcribe từng segment, 
    ghép lại thành 1 transcript hoàn chỉnh,
    sau đó lưu vào CSV.
    """
    base_filename = os.path.basename(file_path)
    logging.info(f"[START] Transcribing: {base_filename}")
    transcription = ""

    try:
        file_segments_dir = os.path.join(SEGMENTS_FOLDER, os.path.splitext(base_filename)[0])
        os.makedirs(file_segments_dir, exist_ok=True)

        # Tạo pattern cho segment đầu ra
        output_pattern = os.path.join(file_segments_dir, f"{base_filename}_%03d.wav")

        # Chia file gốc thành các segment 30 giây
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

        # Nhận diện ngôn ngữ từ segment đầu tiên
        segments, info = model.transcribe(segment_files[0], beam_size=5)
        detected_lang = info.language
        logging.info(f"[INFO] Detected Language: {detected_lang}")

        # Xử lý từng segment
        with tqdm(total=len(segment_files), desc=f"Processing {base_filename}", unit="segment") as pbar:
            for seg in segment_files:
                segments, _ = model.transcribe(seg, language=detected_lang, beam_size=5)
                for segment in segments:
                    transcription += " " + segment.text

                # Làm sạch tạm thời & cập nhật CSV sau mỗi segment
                cleaned_partial = clean_hallucinations(transcription.strip())
                update_csv(base_filename, cleaned_partial)

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
