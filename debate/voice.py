"""Voice Debate Generator module.

Generates an audio dramatization of the debate transcript using pyttsx3.
Assigns distinct speech rate and voice properties to each agent persona.
Fails gracefully if pyttsx3 or audio drivers are unavailable.
"""

import logging
from pathlib import Path
from typing import Optional
from debate.orchestrator import DebateResult

logger = logging.getLogger("voice_debate")


class VoiceDebateGenerator:
    """Generates audio files from DebateResult transcripts using text-to-speech."""

    @staticmethod
    def generate_debate_audio(debate_result: DebateResult, output_path: Path) -> Optional[bytes]:
        """Generate a sequential WAV audio dramatization of all debate rebuttals.

        Returns audio bytes if successful, or None if TTS fails/is unavailable.
        """
        try:
            import pyttsx3
        except ImportError:
            logger.warning("pyttsx3 library not installed. Voice synthesis unavailable.")
            return None

        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")

            # Map personas to voice index and speech rate
            # If multiple voices exist (e.g. David & Zira on Windows), alternate voices
            voice_male = voices[0].id if voices else None
            voice_female = voices[1].id if len(voices) > 1 else voice_male

            PERSONA_VOICE_SETTINGS = {
                "Technical Lead Agent": {"voice": voice_male, "rate": 175},
                "HR & Culture Specialist Agent": {"voice": voice_female, "rate": 185},
                "Engineering Director Agent": {"voice": voice_male, "rate": 160},
                "Risk & Security Skeptic Agent": {"voice": voice_female if len(voices) > 1 else voice_male, "rate": 150},
            }

            # Build script lines — ONLY character name and what they say
            full_audio_script = []
            full_audio_script.append(f"Hiring Panel Debate for candidate {debate_result.candidate_name}.\n\n")

            for reb in debate_result.debate_transcript:
                full_audio_script.append(f"{reb.agent_name} says: {reb.updated_rationale}\n\n")

            script_text = "".join(full_audio_script)

            output_path.parent.mkdir(exist_ok=True)
            engine.save_to_file(script_text, str(output_path))
            engine.runAndWait()
            engine.stop()
            del engine

            # Retry reading bytes to handle temporary SAPI5 Windows file lock
            import time
            audio_bytes = None
            for _ in range(10):
                try:
                    if output_path.exists() and output_path.stat().st_size > 0:
                        audio_bytes = output_path.read_bytes()
                        break
                except PermissionError:
                    time.sleep(0.3)

            if audio_bytes:
                logger.info(f"Successfully generated debate audio bytes for {output_path}")
                return audio_bytes
            else:
                logger.warning("pyttsx3 audio generation produced empty file or locked handle.")
                return None

        except Exception as e:
            logger.warning(f"Voice synthesis failed gracefully: {e}")
            return None
