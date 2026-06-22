"""
Configuration module for Auto Subtitler.
Manages API keys, supported languages, and default settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (override system vars)
load_dotenv(override=True)

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- FFmpeg Path ---
# Check for bundled FFmpeg first, then fall back to system PATH
FFMPEG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin")
FFMPEG_PATH = os.path.join(FFMPEG_DIR, "ffmpeg.exe") if os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg.exe")) else "ffmpeg"
FFPROBE_PATH = os.path.join(FFMPEG_DIR, "ffprobe.exe") if os.path.exists(os.path.join(FFMPEG_DIR, "ffprobe.exe")) else "ffprobe"

# --- Whisper Settings ---
WHISPER_MODEL = "whisper-large-v3"  # Groq's hosted model
MAX_AUDIO_CHUNK_SIZE_MB = 24  # Stay under Groq's 25MB limit
CHUNK_DURATION_MINUTES = 10  # ~10 min chunks for safety

# --- Translation Settings ---
GEMINI_MODEL = "gemini-2.5-flash"
TRANSLATION_BATCH_SIZE = 30  # Segments per API call
TRANSLATION_CONTEXT_WINDOW = 3  # Previous/next segments for context

# --- Subtitle Styling (ASS format for FFmpeg) ---
SUBTITLE_STYLE = {
    "FontName": "Segoe UI",
    "FontSize": "18",
    "PrimaryColour": "&H00FFFFFF",  # White (BBGGRR)
    "OutlineColour": "&H00000000",  # Black
    "Outline": "2",
    "Shadow": "1",
    "Alignment": "2",  # Bottom center
    "MarginV": "25",
}

# --- Supported Languages ---
# Map of language code -> display name
SUPPORTED_LANGUAGES = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "be": "Belarusian",
    "bs": "Bosnian",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "zh": "Chinese",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "gl": "Galician",
    "de": "German",
    "el": "Greek",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "ko": "Korean",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mk": "Macedonian",
    "ms": "Malay",
    "mr": "Marathi",
    "mi": "Maori",
    "ne": "Nepali",
    "no": "Norwegian",
    "fa": "Persian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sr": "Serbian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "es": "Spanish",
    "sw": "Swahili",
    "sv": "Swedish",
    "tl": "Tagalog",
    "ta": "Tamil",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "cy": "Welsh",
}

# Reverse lookup: display name -> code
LANGUAGE_NAME_TO_CODE = {v: k for k, v in SUPPORTED_LANGUAGES.items()}

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
