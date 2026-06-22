"""
Translator module.
Uses Google Gemini API for context-aware subtitle translation.
Sends segments in batches with surrounding context for consistency.
Uses Pydantic structured output for guaranteed response format.
"""

import time
import json
from google import genai
from pydantic import BaseModel
from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    TRANSLATION_BATCH_SIZE, TRANSLATION_CONTEXT_WINDOW,
    SUPPORTED_LANGUAGES
)


class TranslatedSegment(BaseModel):
    """A single translated segment."""
    index: int
    translated_text: str


class TranslationBatch(BaseModel):
    """Batch of translated segments."""
    segments: list[TranslatedSegment]


def _get_language_name(lang_code: str) -> str:
    """Convert language code to display name."""
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


def _build_translation_prompt(
    segments_batch: list,
    source_lang: str,
    target_lang: str,
    prev_context: str = "",
    next_context: str = ""
) -> str:
    """Build the translation prompt with context for a batch of segments."""
    source_name = _get_language_name(source_lang)
    target_name = _get_language_name(target_lang)
    
    segments_text = "\n".join(
        f"{i}: {seg.text}" for i, seg in enumerate(segments_batch)
    )
    
    prompt = f"""You are a professional subtitle translator specializing in {source_name} to {target_name} translation.

Translate the following subtitle segments from {source_name} to {target_name}.

CRITICAL RULES:
1. Keep translations CONCISE — these are on-screen subtitles with limited space (max ~42 characters per line)
2. Preserve the speaker's tone, register, and emotion
3. Adapt idioms and expressions naturally — do NOT translate them literally
4. Keep proper nouns, brand names, and technical terms as-is unless there is a well-known {target_name} equivalent
5. Maintain consistent terminology across all segments (same names, terms)
6. If a segment contains only a sound effect or non-speech (like "[Music]", "[Applause]"), translate the label appropriately
7. Return EXACTLY the same number of segments as provided, in the same order
8. Each translation should be natural and fluent in {target_name}"""

    if prev_context:
        prompt += f"""

PREVIOUS CONTEXT (already translated, for reference only — do NOT include in output):
{prev_context}"""

    if next_context:
        prompt += f"""

UPCOMING CONTEXT (not yet translated, for reference only — do NOT include in output):
{next_context}"""

    prompt += f"""

SEGMENTS TO TRANSLATE (index: original text):
{segments_text}

Return a JSON object with a "segments" array. Each element must have "index" (matching the input index) and "translated_text" (the translation)."""

    return prompt


def translate_segments(
    segments: list,
    source_lang: str,
    target_lang: str,
    progress_callback=None
) -> list:
    """
    Translate all segments using Gemini API in context-aware batches.
    
    Args:
        segments: List of TranscriptSegment objects with .text attribute.
        source_lang: Source language code (e.g., "en").
        target_lang: Target language code (e.g., "ar").
        progress_callback: Optional callback(message, progress_fraction).
        
    Returns:
        List of segments with translated text (same objects, .text modified).
    """
    # Skip if same language
    if source_lang == target_lang:
        if progress_callback:
            progress_callback("Source and target language are the same — skipping translation.", 1.0)
        return segments
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    batch_size = TRANSLATION_BATCH_SIZE
    context_window = TRANSLATION_CONTEXT_WINDOW
    total_batches = (len(segments) + batch_size - 1) // batch_size
    
    translated_texts = {}  # index -> translated text
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(segments))
        batch = segments[start_idx:end_idx]
        
        if progress_callback:
            progress_callback(
                f"Translating batch {batch_idx + 1}/{total_batches} "
                f"(segments {start_idx + 1}-{end_idx}/{len(segments)})...",
                batch_idx / total_batches
            )
        
        # Build context from surrounding segments
        prev_context = ""
        if start_idx > 0:
            prev_segs = segments[max(0, start_idx - context_window):start_idx]
            prev_texts = [
                translated_texts.get(max(0, start_idx - context_window) + j, seg.text)
                for j, seg in enumerate(prev_segs)
            ]
            prev_context = "\n".join(prev_texts)
        
        next_context = ""
        if end_idx < len(segments):
            next_segs = segments[end_idx:min(end_idx + context_window, len(segments))]
            next_context = "\n".join(seg.text for seg in next_segs)
        
        # Build prompt
        prompt = _build_translation_prompt(
            batch, source_lang, target_lang, prev_context, next_context
        )
        
        # Call Gemini API with retry logic
        translations = _call_gemini_with_retry(client, prompt, len(batch))
        
        # Store translations
        for trans in translations:
            abs_idx = start_idx + trans.index
            if 0 <= abs_idx < len(segments):
                translated_texts[abs_idx] = trans.translated_text
    
    # Apply translations to segments
    for i, seg in enumerate(segments):
        if i in translated_texts:
            seg.text = translated_texts[i]
    
    if progress_callback:
        progress_callback(
            f"Translation complete: {len(translated_texts)}/{len(segments)} segments translated.",
            1.0
        )
    
    return segments


def _call_gemini_with_retry(
    client: genai.Client,
    prompt: str,
    expected_count: int,
    max_retries: int = 3
) -> list[TranslatedSegment]:
    """
    Call Gemini API with structured output and retry logic.
    
    Falls back to text parsing if structured output fails.
    """
    for attempt in range(max_retries):
        try:
            # Try structured output first
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": TranslationBatch,
                },
            )
            
            # Parse structured response
            if hasattr(response, "parsed") and response.parsed:
                result = response.parsed
                if len(result.segments) == expected_count:
                    return result.segments
            
            # Fallback: parse the text response as JSON
            text = response.text.strip()
            if text:
                data = json.loads(text)
                segments_data = data.get("segments", data) if isinstance(data, dict) else data
                return [
                    TranslatedSegment(index=s["index"], translated_text=s["translated_text"])
                    for s in segments_data
                ]
                
        except Exception as e:
            error_msg = str(e)
            
            # Rate limit — wait and retry
            if "429" in error_msg or "quota" in error_msg.lower():
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                print(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            
            # Other errors — retry with backoff
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"Translation error (attempt {attempt + 1}): {error_msg}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            raise RuntimeError(f"Translation failed after {max_retries} attempts: {error_msg}")
    
    # If all retries failed to get correct count, return what we have
    return [
        TranslatedSegment(index=i, translated_text=f"[Translation failed]")
        for i in range(expected_count)
    ]
