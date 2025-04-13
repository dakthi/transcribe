import os
import re
import subprocess

def sanitize_path(file_path):
    """
    Cleans up the file path (handles drag-and-drop from mac).
    - Removes quotes
    - Expands ~
    - Converts to absolute path
    """
    file_path = file_path.strip().strip("'")
    file_path = os.path.expanduser(file_path)
    file_path = os.path.abspath(file_path)
    return file_path

def detect_silence(input_file, silence_db=-40, min_silence_duration=0.5):
    """
    Runs ffmpeg with silencedetect to find silent sections.
    Returns a list of dicts: [{start, end, duration}, ...].
    """
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-af", f"silencedetect=n={silence_db}dB:d={min_silence_duration}",
        "-f", "null",
        "-"
    ]
    process = subprocess.run(cmd, capture_output=True, text=True)
    stderr = process.stderr

    starts = re.findall(r"silence_start:\s*([0-9\.]+)", stderr)
    ends   = re.findall(r"silence_end:\s*([0-9\.]+)", stderr)
    durs   = re.findall(r"silence_duration:\s*([0-9\.]+)", stderr)

    silence_data = []
    for i in range(len(ends)):
        silence_data.append({
            "start": float(starts[i]) if i < len(starts) else None,
            "end":   float(ends[i]),
            "duration": float(durs[i]) if i < len(durs) else None
        })

    return silence_data

def generate_silence_report(file_path, silence_info):
    """Saves the silence detection report to a text file."""
    base, _ = os.path.splitext(file_path)
    out_file = f"{base}_silence_report.txt"

    with open(out_file, "w") as f:
        if not silence_info:
            f.write("No silence detected.\n")
        else:
            for i, s in enumerate(silence_info, start=1):
                f.write(f"Silence {i}:\n")
                f.write(f"  Start:    {s['start']} seconds\n")
                f.write(f"  End:      {s['end']} seconds\n")
                f.write(f"  Duration: {s['duration']} seconds\n\n")

    return out_file

def remove_silence(input_file, silence_info):
    """Concatenates non-silent segments into a new file for both video and audio."""
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_removed_silence{ext}"

    if not silence_info:
        print(f"No silence detected in {input_file}. Copying original file.")
        subprocess.run(["cp", input_file, output_file])
        return output_file

    silence_starts = [s['start'] for s in silence_info if s['start'] is not None]
    silence_ends = [s['end'] for s in silence_info]

    filter_complex = ""
    last_end = 0
    segment_count = 0
    for start, end in zip(silence_starts, silence_ends):
        if last_end < start:
            filter_complex += f"[0:v]trim=start={last_end}:end={start},setpts=PTS-STARTPTS[v{segment_count}];"
            filter_complex += f"[0:a]atrim=start={last_end}:end={start},asetpts=PTS-STARTPTS[a{segment_count}];"
            segment_count += 1
        last_end = end

    filter_complex += f"[0:v]trim=start={last_end},setpts=PTS-STARTPTS[v{segment_count}];"
    filter_complex += f"[0:a]atrim=start={last_end},asetpts=PTS-STARTPTS[a{segment_count}];"

    outputs_v = "".join(f"[v{i}]" for i in range(segment_count + 1))
    outputs_a = "".join(f"[a{i}]" for i in range(segment_count + 1))
    filter_complex += f"{outputs_v}concat=n={segment_count+1}:v=1:a=0[outv];"
    filter_complex += f"{outputs_a}concat=n={segment_count+1}:v=0:a=1[outa]"

    cmd = [
        "ffmpeg", "-i", input_file,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        output_file
    ]

    subprocess.run(cmd, check=True)
    return output_file

def reencode_video(input_file, preset="tiktok"):
    base, _ = os.path.splitext(input_file)
    output_file = f"{base}_{preset}.mp4"

    settings = {
        "crf": "20",
        "scale": "1080:1920",
        "preset": "slow",
        "pix_fmt": "yuv420p",
        "bitrate_audio": "128k",
        "timescale": "30000"
    }

    if preset == "highest":
        settings.update({
            "crf": "18",
            "preset": "veryslow",
            "timescale": "90000"
        })
    elif preset == "youtube":
        settings.update({
            "scale": "1920:1080",
            "crf": "21"
        })
    elif preset == "facebook":
        settings.update({
            "crf": "22",
            "scale": "1080:1350"
        })
    elif preset == "instagram":
        settings.update({
            "scale": "1080:1350",
            "crf": "21"
        })

    cmd = [
        "ffmpeg", "-i", input_file,
        "-c:v", "libx264",
        "-preset", settings["preset"],
        "-crf", settings["crf"],
        "-pix_fmt", settings["pix_fmt"],
        "-vf", f"scale={settings['scale']}:flags=lanczos",
        "-c:a", "aac",
        "-b:a", settings["bitrate_audio"],
        "-video_track_timescale", settings["timescale"],
        "-movflags", "+faststart",
        output_file
    ]

    subprocess.run(cmd, check=True)
    return output_file

def process_video(input_file, preset="tiktok"):
    print(f"🔍 Detecting silence in: {input_file}")
    silence_info = detect_silence(input_file)
    generate_silence_report(input_file, silence_info)
    print(f"🪄 Removing silence from: {input_file}")
    cleaned = remove_silence(input_file, silence_info)
    print(f"🎞 Re-encoding for preset: {preset}")
    final_output = reencode_video(cleaned, preset)
    print(f"✅ Done! Output saved at: {final_output}")
    return final_output

def process_folder(folder_path, preset="tiktok"):
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if os.path.isfile(full_path) and file.lower().endswith(('.mp4', '.mov', '.mkv')):
            try:
                process_video(full_path, preset)
            except subprocess.CalledProcessError as e:
                print(f"❌ Error processing {file}: {e}")

if __name__ == "__main__":
    folder_path = input("📁 Enter the path to your video folder: ").strip()
    folder_path = sanitize_path(folder_path)
    preset = input("🎯 Enter preset (tiktok, highest, youtube, facebook, instagram) [default: tiktok]: ").strip() or "tiktok"

    if os.path.isdir(folder_path):
        process_folder(folder_path, preset=preset)
    else:
        print("❌ Invalid folder path. Please try again.")