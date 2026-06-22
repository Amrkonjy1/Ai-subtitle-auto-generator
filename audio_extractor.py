"""
Audio Extractor module.
Extracts audio from video files using FFmpeg and splits into chunks
for Groq Whisper API (25MB file size limit).
"""

import os
import subprocess
import json
import math
from config import FFMPEG_PATH, FFPROBE_PATH, TEMP_DIR, MAX_AUDIO_CHUNK_SIZE_MB, CHUNK_DURATION_MINUTES


def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file in seconds using ffprobe."""
    cmd = [
        FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to get video duration: {e}")


def extract_full_audio(video_path: str, output_path: str = None) -> str:
    """
    Extract audio from video as 16kHz mono WAV (optimal for Whisper).
    
    Args:
        video_path: Path to the input video file.
        output_path: Optional path for the output WAV. Auto-generated if None.
        
    Returns:
        Path to the extracted WAV file.
    """
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(TEMP_DIR, f"{base_name}_audio.wav")
    
    cmd = [
        FFMPEG_PATH,
        "-y",                    # Overwrite output
        "-i", video_path,        # Input video
        "-vn",                   # Disable video
        "-acodec", "pcm_s16le",  # WAV PCM format
        "-ar", "16000",          # 16kHz sample rate (Whisper optimal)
        "-ac", "1",              # Mono channel
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr}")
    
    if not os.path.exists(output_path):
        raise RuntimeError("Audio extraction produced no output file.")
    
    return output_path


def split_audio_into_chunks(audio_path: str, chunk_duration_sec: int = None) -> list[str]:
    """
    Split a WAV audio file into chunks that fit within Groq's size limit.
    
    For 16kHz mono 16-bit PCM WAV:
    - 1 second = 16000 samples × 2 bytes = 32,000 bytes ≈ 31.25 KB
    - 10 minutes = 18.75 MB (safely under 25MB)
    
    Args:
        audio_path: Path to the full WAV audio file.
        chunk_duration_sec: Duration of each chunk in seconds. Auto-calculated if None.
        
    Returns:
        List of paths to audio chunk files.
    """
    if chunk_duration_sec is None:
        chunk_duration_sec = CHUNK_DURATION_MINUTES * 60  # 10 minutes default
    
    # Get total audio duration
    duration = get_video_duration(audio_path)
    
    # Check if file is small enough to skip chunking
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb <= MAX_AUDIO_CHUNK_SIZE_MB:
        return [audio_path]
    
    # Calculate number of chunks needed
    num_chunks = math.ceil(duration / chunk_duration_sec)
    chunk_paths = []
    
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    
    for i in range(num_chunks):
        start_time = i * chunk_duration_sec
        chunk_path = os.path.join(TEMP_DIR, f"{base_name}_chunk_{i:03d}.wav")
        
        cmd = [
            FFMPEG_PATH,
            "-y",
            "-i", audio_path,
            "-ss", str(start_time),
            "-t", str(chunk_duration_sec),
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            chunk_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 44:  # WAV header is 44 bytes
                chunk_paths.append(chunk_path)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to create chunk {i}: {e.stderr}")
    
    if not chunk_paths:
        raise RuntimeError("Audio chunking produced no valid chunks.")
    
    return chunk_paths


def extract_and_chunk(video_path: str, progress_callback=None) -> tuple[list[str], float]:
    """
    Full extraction pipeline: extract audio from video and split into chunks.
    
    Args:
        video_path: Path to the input video file.
        progress_callback: Optional callback(message, progress_fraction) for UI updates.
        
    Returns:
        Tuple of (list of chunk file paths, total duration in seconds).
    """
    if progress_callback:
        progress_callback("Getting video information...", 0.0)
    
    duration = get_video_duration(video_path)
    
    if progress_callback:
        progress_callback(f"Extracting audio ({duration:.0f}s video)...", 0.1)
    
    audio_path = extract_full_audio(video_path)
    
    if progress_callback:
        progress_callback("Splitting audio into chunks...", 0.5)
    
    chunks = split_audio_into_chunks(audio_path)
    
    if progress_callback:
        progress_callback(f"Audio ready: {len(chunks)} chunk(s)", 1.0)
    
    return chunks, duration


def cleanup_temp_files():
    """Remove all temporary audio files."""
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            filepath = os.path.join(TEMP_DIR, f)
            try:
                os.remove(filepath)
            except OSError:
                pass
