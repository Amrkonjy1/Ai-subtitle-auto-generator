"""
Pipeline module.
Orchestrates the full auto-subtitling workflow:
  Extract audio → Transcribe → Translate → Generate SRT → Burn subtitles
"""

import os
from audio_extractor import extract_and_chunk, cleanup_temp_files
from transcriber import transcribe_audio
from translator import translate_segments
from srt_generator import generate_srt, srt_to_text, text_to_srt_file
from video_processor import burn_subtitles
from config import SUPPORTED_LANGUAGES, OUTPUT_DIR
import copy


def run_transcription_pipeline(
    video_path: str,
    target_lang: str,
    source_lang: str = None,
    progress_callback=None
) -> tuple[str, str, str]:
    """
    Run the transcription and translation pipeline (Phase 1).
    Produces an SRT file for user review.
    
    Args:
        video_path: Path to the input video file.
        target_lang: Target language code (e.g., "ar", "en").
        source_lang: Source language code. If None, auto-detected.
        progress_callback: Optional callback(message, progress_fraction).
        
    Returns:
        Tuple of (srt_content, detected_language, srt_file_path).
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Step 1: Extract audio and split into chunks
    _progress(progress_callback, "Step 1/4: Extracting audio from video...", 0.0)
    audio_chunks, duration = extract_and_chunk(
        video_path,
        progress_callback=lambda msg, p: _progress(progress_callback, f"{msg}", p * 0.15)
    )
    
    # Step 2: Transcribe with Groq Whisper API
    _progress(progress_callback, "Step 2/4: Transcribing audio (Groq Whisper)...", 0.15)
    segments, detected_lang = transcribe_audio(
        audio_chunks,
        language=source_lang,
        progress_callback=lambda msg, p: _progress(progress_callback, f"{msg}", 0.15 + p * 0.35)
    )
    
    if not segments:
        raise RuntimeError("Transcription produced no segments. The audio may be silent or corrupted.")
    
    # Step 3: Translate if needed
    needs_translation = target_lang and target_lang != detected_lang
    
    if needs_translation:
        _progress(progress_callback, f"Step 3/4: Translating {len(segments)} segments ({detected_lang} → {target_lang})...", 0.50)
        # Deep copy segments so we keep original text for reference
        segments = copy.deepcopy(segments)
        segments = translate_segments(
            segments,
            source_lang=detected_lang,
            target_lang=target_lang,
            progress_callback=lambda msg, p: _progress(progress_callback, f"{msg}", 0.50 + p * 0.35)
        )
    else:
        _progress(progress_callback, "Step 3/4: No translation needed (same language).", 0.85)
    
    # Step 4: Generate SRT file
    _progress(progress_callback, "Step 4/4: Generating SRT file...", 0.85)
    srt_path = generate_srt(segments, video_name=video_name)
    srt_content = srt_to_text(srt_path)
    
    detected_lang_name = SUPPORTED_LANGUAGES.get(detected_lang, detected_lang)
    _progress(
        progress_callback,
        f"Done! Detected language: {detected_lang_name}. "
        f"Generated {len(segments)} subtitle segments. "
        f"Review the SRT below and click 'Burn Subtitles' when ready.",
        1.0
    )
    
    return srt_content, detected_lang, srt_path


def run_burn_pipeline(
    video_path: str,
    srt_content: str,
    progress_callback=None
) -> tuple[str, str]:
    """
    Run the subtitle burning pipeline (Phase 2).
    Takes reviewed/edited SRT and burns it into the video.
    
    Args:
        video_path: Path to the original video file.
        srt_content: The (potentially edited) SRT content as text.
        progress_callback: Optional callback(message, progress_fraction).
        
    Returns:
        Tuple of (output_video_path, srt_file_path).
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Save the (potentially edited) SRT content
    srt_path = os.path.join(OUTPUT_DIR, f"{video_name}.srt")
    text_to_srt_file(srt_content, srt_path)
    
    # Burn subtitles into video
    _progress(progress_callback, "Burning subtitles into video...", 0.1)
    output_video = burn_subtitles(
        video_path,
        srt_path,
        progress_callback=lambda msg, p: _progress(progress_callback, f"{msg}", 0.1 + p * 0.9)
    )
    
    _progress(progress_callback, "Video with subtitles is ready!", 1.0)
    
    # Clean up temp files
    try:
        cleanup_temp_files()
    except Exception:
        pass  # Non-critical
    
    return output_video, srt_path


def _progress(callback, message, fraction):
    """Safe progress callback wrapper."""
    if callback:
        callback(message, fraction)
