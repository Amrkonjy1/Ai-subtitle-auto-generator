"""
SRT Generator module.
Converts transcript segments to standard SRT subtitle format.
Handles line wrapping, timestamp formatting, and segment merging.
"""

import pysrt
from pysrt import SubRipItem, SubRipTime, SubRipFile
import os
from config import OUTPUT_DIR


def seconds_to_srt_time(seconds: float) -> SubRipTime:
    """Convert seconds (float) to pysrt SubRipTime."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return SubRipTime(hours=hours, minutes=minutes, seconds=secs, milliseconds=millis)


def wrap_text(text: str, max_chars_per_line: int = 42, max_lines: int = 2) -> str:
    """
    Wrap subtitle text to fit on screen.
    
    Args:
        text: The subtitle text to wrap.
        max_chars_per_line: Maximum characters per line (standard is ~42).
        max_lines: Maximum number of lines (standard is 2).
        
    Returns:
        Wrapped text with newlines.
    """
    # If text already fits on one line, return as-is
    if len(text) <= max_chars_per_line:
        return text
    
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_len = len(word) + (1 if current_line else 0)  # +1 for space
        
        if current_length + word_len > max_chars_per_line and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
            
            if len(lines) >= max_lines:
                # Max lines reached — append remaining words to last line
                remaining = words[words.index(word):]
                lines[-1] = " ".join([lines[-1]] + remaining[1:]) if len(remaining) > 1 else lines[-1]
                lines.append(word)
                break
        else:
            current_line.append(word)
            current_length += word_len
    
    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))
    elif current_line:
        # Append to last line if max lines reached
        lines[-1] += " " + " ".join(current_line)
    
    return "\n".join(lines[:max_lines])


def merge_short_segments(segments: list, min_duration: float = 0.5, min_gap: float = 0.3) -> list:
    """
    Merge very short consecutive segments for better readability.
    
    Args:
        segments: List of transcript segments.
        min_duration: Minimum duration for a segment (seconds).
        min_gap: Maximum gap between segments to merge (seconds).
        
    Returns:
        List of merged segments.
    """
    if not segments:
        return segments
    
    merged = [segments[0]]
    
    for seg in segments[1:]:
        prev = merged[-1]
        gap = seg.start - prev.end
        prev_duration = prev.end - prev.start
        
        # Merge if previous segment is very short and gap is small
        if prev_duration < min_duration and gap < min_gap:
            prev.end = seg.end
            prev.text = prev.text.rstrip() + " " + seg.text.lstrip()
        else:
            merged.append(seg)
    
    return merged


def generate_srt(segments: list, output_path: str = None, video_name: str = "output") -> str:
    """
    Generate an SRT file from transcript segments.
    
    Args:
        segments: List of transcript segments with .start, .end, .text attributes.
        output_path: Optional output file path. Auto-generated if None.
        video_name: Base name for auto-generated output path.
        
    Returns:
        Path to the generated SRT file.
    """
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"{video_name}.srt")
    
    # Merge very short segments
    segments = merge_short_segments(segments)
    
    # Create SRT file
    srt_file = SubRipFile()
    
    for i, seg in enumerate(segments):
        # Wrap text for readability
        wrapped_text = wrap_text(seg.text.strip())
        
        item = SubRipItem(
            index=i + 1,
            start=seconds_to_srt_time(seg.start),
            end=seconds_to_srt_time(seg.end),
            text=wrapped_text
        )
        srt_file.append(item)
    
    # Save with UTF-8 encoding (critical for non-Latin scripts)
    srt_file.save(output_path, encoding="utf-8")
    
    return output_path


def srt_to_text(srt_path: str) -> str:
    """Read an SRT file and return its content as plain text."""
    with open(srt_path, "r", encoding="utf-8") as f:
        return f.read()


def text_to_srt_file(srt_text: str, output_path: str) -> str:
    """
    Save edited SRT text content to a file.
    Used when the user edits the SRT in the UI.
    
    Args:
        srt_text: The SRT content as a string.
        output_path: Where to save the file.
        
    Returns:
        Path to the saved SRT file.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_text)
    
    return output_path


def parse_srt_text(srt_text: str) -> SubRipFile:
    """Parse SRT text content into a SubRipFile object for validation."""
    import tempfile
    
    # Write to temp file for pysrt to parse
    with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8") as f:
        f.write(srt_text)
        temp_path = f.name
    
    try:
        srt_file = pysrt.open(temp_path, encoding="utf-8")
        return srt_file
    finally:
        os.unlink(temp_path)
