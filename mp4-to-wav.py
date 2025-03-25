import subprocess
import os

def sanitize_path(file_path):
    """
    Cleans up the file path (handles drag-and-drop from mac).
    - Removes quotes
    - Expands ~
    - Converts to absolute path
    """
    file_path = file_path.strip()
    file_path = file_path.strip("'")
    file_path = os.path.expanduser(file_path)
    file_path = os.path.abspath(file_path)
    return file_path

def convert_mp4_to_wav():
    # Prompt the user for the input MP4 file
    input_file = input("Enter the path to the MP4 file: ")
    input_file = sanitize_path(input_file)

    # Ensure the file exists
    if not os.path.exists(input_file):
        print("Error: File not found.")
        return

    # Set the output WAV file name
    output_file = os.path.splitext(input_file)[0] + ".wav"

    # Construct and run the ffmpeg command
    command = [
        "ffmpeg",
        "-i", input_file,
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        output_file
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Conversion successful! Output saved as {output_file}")
    except subprocess.CalledProcessError as e:
        print("Error during conversion:", e)

if __name__ == "__main__":
    convert_mp4_to_wav()
