<div align="center">
  <h1>Auto Subtitler</h1>
  <p>
    <strong>A high-performance, AI-driven video transcription and translation pipeline.</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python Version" />
    <img src="https://img.shields.io/badge/FFmpeg-Enabled-green?style=for-the-badge&logo=ffmpeg" alt="FFmpeg" />
    <img src="https://img.shields.io/badge/Gradio-UI-orange?style=for-the-badge&logo=gradio" alt="Gradio UI" />
  </p>
</div>

---

## 📌 Overview

**Auto Subtitler** is a production-grade application designed to automate the process of adding high-quality, localized subtitles to any video. 

By leveraging the speed of **Groq's Whisper API** and the contextual intelligence of **Google's Gemini API**, this tool extracts audio, transcribes it with segment-level timestamp precision, translates the text into over 90 languages, and hardcodes (burns) the subtitles directly back into the video—all through a clean, modern web interface.

## ✨ Key Features

- **Blazing Fast Transcription:** Uses Groq's API to transcribe audio in a fraction of the time it takes locally.
- **Context-Aware AI Translation:** Employs Gemini to translate subtitles in batches, preserving surrounding context to maintain idioms, names, and tone.
- **Smart Audio Chunking:** Automatically splits large video files into optimal segments to bypass strict API payload limits (e.g., 25MB), dynamically recalculating timestamp offsets on the fly.
- **Human-in-the-Loop Review:** Provides an editable SRT text interface, allowing you to review and perfect subtitles before rendering the final video.
- **Zero Local GPU Required:** Completely cloud-accelerated processing. 
- **Bundled Processing:** Integrates directly with FFmpeg via Python subprocesses to cleanly extract audio and burn `.ass` styled subtitles.

---

## 🛠️ How It Works (The Pipeline)

The architecture is built on a streamlined, two-phase execution model:

### Phase 1: AI Extraction & Generation
1. **Audio Extraction:** FFmpeg strips the audio track from the uploaded video.
2. **Chunking & Offsets:** Audio is sliced into API-friendly chunks (<25MB).
3. **Transcription:** Groq's Whisper model transcribes the chunks, returning highly accurate segment-level timestamps.
4. **Contextual Translation:** If a target language is requested, the text is fed into Gemini in sliding-window batches to ensure translations make contextual sense.
5. **SRT Compilation:** The parsed text and timestamps are compiled into standard SubRip (`.srt`) format with automated line-wrapping for screen readability.

### Phase 2: Review & Render
6. **User Review:** The generated SRT is presented in the Gradio UI for manual review or correction.
7. **Subtitle Burning:** Upon approval, FFmpeg burns the subtitles into the video frames using custom `libass` styling (Segoe UI, clean drop-shadows) ensuring cross-device compatibility.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- [Groq API Key](https://console.groq.com/keys)
- [Gemini API Key](https://aistudio.google.com/apikey)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/auto-subtitler.git
   cd auto-subtitler
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: A portable build of FFmpeg is required. You can place `ffmpeg.exe` inside a local `ffmpeg_bin/` folder or ensure it is accessible in your system PATH).*

3. **Environment Setup:**
   Create a `.env` file in the root directory and add your keys:
   ```env
   GEMINI_API_KEY=your_gemini_key_here
   GROQ_API_KEY=your_groq_key_here
   ```

### Execution

Run the provided batch file or execute the python script directly:

```bash
# Windows
run.bat

# Or manually
python app.py
```

The application will launch a local server. Open `http://localhost:7860` in your web browser to access the interface.

---

## 📂 Project Structure

- `app.py`: The Gradio web application interface and state management.
- `pipeline.py`: The orchestrator that chains transcription, translation, and rendering.
- `audio_extractor.py`: FFmpeg subprocess logic for efficient audio extraction and chunking.
- `transcriber.py`: Groq Whisper API client integration and timestamp alignment.
- `translator.py`: Gemini API client using Pydantic structured outputs for reliable batch translation.
- `srt_generator.py`: Formatting logic utilizing `pysrt` for text wrapping and segment merging.
- `video_processor.py`: FFmpeg rendering engine for hard-subbing (`libass` style).
- `config.py`: Global configuration, UI styling settings, and supported language mappings.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome. Feel free to check the issues page if you want to contribute.

## 📝 License
This project is open source and available under the [MIT License](LICENSE).
