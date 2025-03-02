import whisper
import torch

model = whisper.load_model("turbo")

# Load and process audio
audio = whisper.load_audio("Barbican Cinema Cafe & Bar 2.m4a")
audio = whisper.pad_or_trim(audio)

# Convert to log-Mel spectrogram
mel = whisper.log_mel_spectrogram(audio).to(torch.float32)  # 🔥 Force FP32

# Move the model to FP32
model = model.to(torch.float32)

# Transcribe the audio
result = model.transcribe("Barbican Cinema Cafe & Bar 2.m4a", fp16=False)

print(result["text"])
