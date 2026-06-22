"""
Auto Subtitler — Gradio Web Interface.
Two-phase workflow:
  Phase 1: Upload video → Transcribe → Translate → Review SRT
  Phase 2: Edit SRT → Burn subtitles → Download final video + SRT
"""

import gradio as gr
import os
from pipeline import run_transcription_pipeline, run_burn_pipeline
from config import SUPPORTED_LANGUAGES, GEMINI_API_KEY, GROQ_API_KEY

# --- State ---
current_video_path = None
current_srt_path = None


def get_language_choices():
    """Get formatted language choices for dropdown."""
    return sorted([f"{name} ({code})" for code, name in SUPPORTED_LANGUAGES.items()])


def parse_language_choice(choice: str) -> str:
    """Extract language code from dropdown choice like 'English (en)'."""
    if not choice:
        return ""
    # Extract code from parentheses
    if "(" in choice and ")" in choice:
        return choice.split("(")[-1].rstrip(")")
    return choice


def phase1_transcribe(video_file, target_language, progress=gr.Progress(track_tqdm=False)):
    """
    Phase 1: Transcribe video and translate subtitles.
    Returns SRT content for review.
    """
    global current_video_path
    
    if video_file is None:
        raise gr.Error("Please upload a video file first!")
    
    # Get the video file path
    video_path = video_file if isinstance(video_file, str) else video_file
    current_video_path = video_path
    
    target_code = parse_language_choice(target_language)
    if not target_code:
        raise gr.Error("Please select a target language!")
    
    # Validate API keys
    if not GROQ_API_KEY:
        raise gr.Error("Groq API key not found! Please check your .env file.")
    if not GEMINI_API_KEY:
        raise gr.Error("Gemini API key not found! Please check your .env file.")
    
    def progress_callback(message, fraction):
        progress(fraction, desc=message)
    
    try:
        srt_content, detected_lang, srt_path = run_transcription_pipeline(
            video_path=video_path,
            target_lang=target_code,
            progress_callback=progress_callback
        )
        
        detected_name = SUPPORTED_LANGUAGES.get(detected_lang, detected_lang)
        status_msg = f"Detected: **{detected_name}** → Target: **{SUPPORTED_LANGUAGES.get(target_code, target_code)}**"
        
        return (
            srt_content,       # SRT text area
            status_msg,        # Status message
            srt_path,          # Hidden SRT path
            gr.update(interactive=True, variant="primary"),  # Enable burn button
        )
        
    except Exception as e:
        raise gr.Error(f"Transcription failed: {str(e)}")


def phase2_burn(video_file, srt_content, progress=gr.Progress(track_tqdm=False)):
    """
    Phase 2: Burn the (edited) SRT into the video.
    """
    if video_file is None:
        raise gr.Error("No video file found! Please upload a video first.")
    
    if not srt_content or not srt_content.strip():
        raise gr.Error("SRT content is empty! Please generate subtitles first.")
    
    video_path = video_file if isinstance(video_file, str) else video_file
    
    def progress_callback(message, fraction):
        progress(fraction, desc=message)
    
    try:
        output_video, output_srt = run_burn_pipeline(
            video_path=video_path,
            srt_content=srt_content,
            progress_callback=progress_callback
        )
        
        return (
            output_video,   # Output video
            output_srt,     # Output SRT file download
            "Subtitled video is ready! Download below."  # Status
        )
        
    except Exception as e:
        raise gr.Error(f"Subtitle burning failed: {str(e)}")


# --- Custom CSS ---
custom_css = """
/* Dark premium theme overrides */
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}

/* Title styling */
.title-text {
    text-align: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5em !important;
    font-weight: 800 !important;
    margin-bottom: 0 !important;
}

.subtitle-text {
    text-align: center;
    color: #888 !important;
    font-size: 1.1em !important;
    margin-top: 0 !important;
}

/* Phase cards */
.phase-card {
    border: 1px solid rgba(102, 126, 234, 0.3) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    background: rgba(102, 126, 234, 0.03) !important;
}

/* Button enhancements */
.primary-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    font-size: 1.1em !important;
    padding: 12px 32px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
}

.burn-btn {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    border: none !important;
    font-size: 1.1em !important;
    padding: 12px 32px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4) !important;
}

.burn-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(245, 87, 108, 0.6) !important;
}

/* Status badge */
.status-box {
    padding: 12px 20px !important;
    border-radius: 12px !important;
    font-weight: 500 !important;
}

/* SRT editor */
.srt-editor textarea {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}

/* Footer */
.footer-text {
    text-align: center;
    color: #666 !important;
    font-size: 0.85em !important;
    margin-top: 20px !important;
}
"""


def create_ui():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(
        title="Auto Subtitler — AI-Powered Video Subtitles",
        css=custom_css,
        theme=gr.themes.Soft(
            primary_hue="violet",
            secondary_hue="purple",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        ),
    ) as app:
        
        # --- Header ---
        gr.HTML("""
            <div style="text-align: center; padding: 20px 0 10px 0;">
                <h1 class="title-text">Auto Subtitler</h1>
                <p class="subtitle-text">AI-powered video transcription & translation • Groq Whisper + Gemini</p>
            </div>
        """)
        
        # Hidden state
        srt_path_state = gr.State(value=None)
        
        # ========================
        # PHASE 1: Transcribe & Translate
        # ========================
        with gr.Group(elem_classes="phase-card"):
            gr.Markdown("### Phase 1: Upload & Transcribe")
            
            with gr.Row():
                with gr.Column(scale=2):
                    video_input = gr.Video(
                        label="Upload Video",
                        sources=["upload"],
                        height=300,
                    )
                
                with gr.Column(scale=1):
                    target_lang = gr.Dropdown(
                        choices=get_language_choices(),
                        value="English (en)",
                        label="Target Subtitle Language",
                        info="The language you want the subtitles in",
                        filterable=True,
                    )
                    
                    transcribe_btn = gr.Button(
                        "Generate Subtitles",
                        variant="primary",
                        size="lg",
                        elem_classes="primary-btn",
                    )
                    
                    status_display = gr.Markdown(
                        value="*Upload a video and click 'Generate Subtitles' to begin.*",
                        elem_classes="status-box",
                    )
        
        # ========================
        # PHASE 2: Review & Burn
        # ========================
        with gr.Group(elem_classes="phase-card"):
            gr.Markdown("### Phase 2: Review & Burn Subtitles")
            gr.Markdown(
                "*Review the generated SRT below. Edit any mistakes, then click 'Burn Subtitles' to embed them in the video.*",
            )
            
            srt_editor = gr.Textbox(
                label="SRT Subtitle Content (editable)",
                placeholder="Subtitles will appear here after transcription...",
                lines=15,
                max_lines=30,
                elem_classes="srt-editor",
                interactive=True,
            )
            
            burn_btn = gr.Button(
                "Burn Subtitles into Video",
                variant="secondary",
                size="lg",
                interactive=False,
                elem_classes="burn-btn",
            )
        
        # ========================
        # OUTPUT
        # ========================
        with gr.Group(elem_classes="phase-card"):
            gr.Markdown("### Output")
            
            with gr.Row():
                with gr.Column(scale=2):
                    output_video = gr.Video(
                        label="Subtitled Video",
                        height=350,
                    )
                
                with gr.Column(scale=1):
                    output_srt = gr.File(
                        label="Download SRT File",
                    )
                    output_status = gr.Markdown(
                        value="*Output will appear here after burning subtitles.*"
                    )
        
        # --- Footer ---
        gr.HTML("""
            <div class="footer-text">
                <p>Powered by <strong>Groq Whisper</strong> (transcription) & <strong>Google Gemini</strong> (translation) & <strong>FFmpeg</strong> (video processing)</p>
            </div>
        """)
        
        # ========================
        # EVENT HANDLERS
        # ========================
        
        # Phase 1: Transcribe
        transcribe_btn.click(
            fn=phase1_transcribe,
            inputs=[video_input, target_lang],
            outputs=[srt_editor, status_display, srt_path_state, burn_btn],
        )
        
        # Phase 2: Burn subtitles
        burn_btn.click(
            fn=phase2_burn,
            inputs=[video_input, srt_editor],
            outputs=[output_video, output_srt, output_status],
        )
    
    return app


# --- Main entry point ---
if __name__ == "__main__":
    app = create_ui()
    app.queue()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
