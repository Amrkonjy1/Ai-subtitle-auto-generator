"""
Video Processor module.
Burns subtitles into video or adds subtitle track using FFmpeg.
"""

import os
import subprocess
import re
from config import FFMPEG_PATH, SUBTITLE_STYLE, OUTPUT_DIR


def _build_style_string() -> str:
    """Build the ASS force_style string from config."""
    parts = [f"{k}={v}" for k, v in SUBTITLE_STYLE.items()]
    return ",".join(parts)


def _escape_path_for_filter(path: str) -> str:
    """
    Escape a file path for use in FFmpeg filter strings.
    FFmpeg filters need forward slashes and special character escaping.
    """
    # Convert backslashes to forward slashes
    escaped = path.replace("\\", "/")
    # Escape colons (except drive letter)
    if len(escaped) > 1 and escaped[1] == ":":
        # Keep drive letter colon, escape others
        escaped = escaped[0] + "\\:" + escaped[2:].replace(":", "\\:")
    # Escape single quotes
    escaped = escaped.replace("'", "\\'")
    return escaped


def burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str = None,
    progress_callback=None
) -> str:
    """
    Burn subtitles (hardsub) into the video using FFmpeg's subtitles filter.
    
    Args:
        video_path: Path to the input video file.
        srt_path: Path to the SRT subtitle file.
        output_path: Optional output path. Auto-generated if None.
        progress_callback: Optional callback(message, progress_fraction).
        
    Returns:
        Path to the output video with burned-in subtitles.
    """
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}_subtitled.mp4")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Escape SRT path for FFmpeg filter
    srt_escaped = _escape_path_for_filter(srt_path)
    style_string = _build_style_string()
    
    # Build FFmpeg command
    subtitle_filter = f"subtitles='{srt_escaped}':force_style='{style_string}'"
    
    cmd = [
        FFMPEG_PATH,
        "-y",                          # Overwrite output
        "-i", video_path,              # Input video
        "-vf", subtitle_filter,        # Subtitle filter
        "-c:v", "libx264",             # H.264 video codec
        "-crf", "23",                  # Quality (lower = better, 23 is default)
        "-preset", "medium",           # Encoding speed/quality tradeoff
        "-c:a", "copy",                # Copy audio without re-encoding
        output_path
    ]
    
    if progress_callback:
        progress_callback("Burning subtitles into video...", 0.1)
    
    try:
        # Run FFmpeg and capture progress
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stderr_output = []
        
        # Read stderr for progress updates
        for line in process.stderr:
            stderr_output.append(line)
            
            # Parse FFmpeg progress from stderr
            if progress_callback and "time=" in line:
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})", line)
                if time_match:
                    h, m, s = map(int, time_match.groups())
                    current_time = h * 3600 + m * 60 + s
                    # We don't know total duration here, so just show time processed
                    progress_callback(
                        f"Processing... {h:02d}:{m:02d}:{s:02d} encoded",
                        0.5  # Approximate
                    )
        
        process.wait()
        
        if process.returncode != 0:
            error_text = "".join(stderr_output[-20:])  # Last 20 lines
            raise RuntimeError(f"FFmpeg failed:\n{error_text}")
        
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg not found! Please ensure FFmpeg is installed.\n"
            "The 'ffmpeg_bin' folder should contain ffmpeg.exe, or FFmpeg should be in your system PATH."
        )
    
    if not os.path.exists(output_path):
        raise RuntimeError("FFmpeg produced no output file.")
    
    if progress_callback:
        progress_callback("Subtitles burned into video successfully!", 1.0)
    
    return output_path


def add_subtitle_track(
    video_path: str,
    srt_path: str,
    output_path: str = None,
    language: str = "eng"
) -> str:
    """
    Add SRT as a soft subtitle track (can be toggled on/off in players).
    
    Args:
        video_path: Path to the input video.
        srt_path: Path to the SRT file.
        output_path: Optional output path.
        language: ISO 639-2 language code for the subtitle track.
        
    Returns:
        Path to the output video with subtitle track.
    """
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        ext = os.path.splitext(video_path)[1] or ".mp4"
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}_softsub{ext}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Determine subtitle codec based on container
    ext = os.path.splitext(output_path)[1].lower()
    sub_codec = "mov_text" if ext == ".mp4" else "srt"
    
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", video_path,
        "-i", srt_path,
        "-map", "0:v",          # Video from first input
        "-map", "0:a",          # Audio from first input
        "-map", "1",            # Subtitles from second input
        "-c", "copy",           # Copy all streams
        "-c:s", sub_codec,      # Subtitle codec
        "-metadata:s:s:0", f"language={language}",
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg softsub failed: {e.stderr}")
    
    return output_path
