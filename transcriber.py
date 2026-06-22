"""
Transcriber module.
Uses Groq Whisper API for cloud-based speech-to-text with timestamps.
Handles chunked audio files and merges results with offset correction.
"""

import os
from dataclasses import dataclass
from groq import Groq
from config import GROQ_API_KEY, WHISPER_MODEL, CHUNK_DURATION_MINUTES


@dataclass
class TranscriptSegment:
    """A single transcribed segment with timing information."""
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: str     # Transcribed text
    
    def __repr__(self):
        return f"[{self.start:.2f}s -> {self.end:.2f}s] {self.text}"


def transcribe_chunk(
    audio_path: str,
    client: Groq,
    language: str = None,
    time_offset: float = 0.0
) -> tuple[list[TranscriptSegment], str]:
    """
    Transcribe a single audio chunk using Groq Whisper API.
    
    Args:
        audio_path: Path to the audio file (WAV, max 25MB).
        client: Initialized Groq client.
        language: Optional language code to force (skips auto-detection).
        time_offset: Offset in seconds to add to all timestamps (for chunked audio).
        
    Returns:
        Tuple of (list of TranscriptSegments, detected language code).
    """
    with open(audio_path, "rb") as f:
        kwargs = {
            "file": (os.path.basename(audio_path), f.read()),
            "model": WHISPER_MODEL,
            "response_format": "verbose_json",
            "timestamp_granularities": ["segment"],
        }
        
        # If language is specified, skip auto-detection for better accuracy
        if language:
            kwargs["language"] = language
        
        transcription = client.audio.transcriptions.create(**kwargs)
    
    # Extract detected language
    detected_lang = getattr(transcription, "language", "unknown")
    
    # Parse segments
    segments = []
    raw_segments = getattr(transcription, "segments", [])
    
    if raw_segments:
        for seg in raw_segments:
            segment = TranscriptSegment(
                start=seg.get("start", seg.start if hasattr(seg, "start") else 0) + time_offset,
                end=seg.get("end", seg.end if hasattr(seg, "end") else 0) + time_offset,
                text=seg.get("text", seg.text if hasattr(seg, "text") else "").strip()
            )
            if segment.text:  # Skip empty segments
                segments.append(segment)
    elif hasattr(transcription, "text") and transcription.text:
        # Fallback: no segments returned, create a single segment from full text
        segments.append(TranscriptSegment(
            start=time_offset,
            end=time_offset + 30.0,  # Approximate
            text=transcription.text.strip()
        ))
    
    return segments, detected_lang


def transcribe_audio(
    audio_chunks: list[str],
    language: str = None,
    progress_callback=None
) -> tuple[list[TranscriptSegment], str, float]:
    """
    Transcribe multiple audio chunks and merge results.
    
    Args:
        audio_chunks: List of paths to audio chunk files.
        language: Optional language code. If None, auto-detects from first chunk.
        progress_callback: Optional callback(message, progress_fraction) for UI updates.
        
    Returns:
        Tuple of (merged segments, detected language code, detection confidence).
    """
    client = Groq(api_key=GROQ_API_KEY)
    
    all_segments = []
    detected_language = None
    chunk_duration = CHUNK_DURATION_MINUTES * 60  # seconds
    
    for i, chunk_path in enumerate(audio_chunks):
        progress = (i / len(audio_chunks))
        if progress_callback:
            progress_callback(
                f"Transcribing chunk {i + 1}/{len(audio_chunks)}...",
                progress
            )
        
        # Calculate time offset for this chunk
        time_offset = i * chunk_duration if len(audio_chunks) > 1 else 0.0
        
        # For the first chunk, let Whisper auto-detect if no language specified
        # For subsequent chunks, use the detected language for consistency
        chunk_lang = language or detected_language
        
        try:
            segments, lang = transcribe_chunk(
                chunk_path, client, chunk_lang, time_offset
            )
            
            # Store detected language from first chunk
            if detected_language is None:
                detected_language = lang
            
            all_segments.extend(segments)
            
        except Exception as e:
            error_msg = str(e)
            if "413" in error_msg or "too large" in error_msg.lower():
                raise RuntimeError(
                    f"Audio chunk {i + 1} exceeds Groq's file size limit. "
                    "Try using a shorter chunk duration."
                )
            raise RuntimeError(f"Transcription failed on chunk {i + 1}: {error_msg}")
    
    if progress_callback:
        progress_callback(
            f"Transcription complete: {len(all_segments)} segments in '{detected_language}'",
            1.0
        )
    
    # Clean up any overlapping segments from chunk boundaries
    all_segments = _merge_boundary_segments(all_segments)
    
    return all_segments, detected_language or "unknown"


def _merge_boundary_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """
    Clean up segments that might overlap at chunk boundaries.
    If two consecutive segments overlap in time, adjust the boundary.
    """
    if len(segments) <= 1:
        return segments
    
    cleaned = [segments[0]]
    for seg in segments[1:]:
        prev = cleaned[-1]
        
        # Fix overlapping timestamps
        if seg.start < prev.end:
            # If they overlap significantly and have similar text, skip the duplicate
            overlap = prev.end - seg.start
            if overlap > 2.0 and _text_similarity(prev.text, seg.text) > 0.5:
                continue  # Skip duplicate
            else:
                # Just adjust the boundary
                seg.start = prev.end
        
        if seg.start < seg.end and seg.text.strip():
            cleaned.append(seg)
    
    return cleaned


def _text_similarity(text1: str, text2: str) -> float:
    """Simple word-overlap similarity between two strings."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)
