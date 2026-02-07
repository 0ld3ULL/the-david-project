"""
DEVA Voice Assistant - Main interaction loop.

Push-to-talk voice interaction:
1. Hold SPACE to speak
2. Release to send to DEVA
3. DEVA responds with voice

Usage:
    python -m voice.voice_assistant
"""

import asyncio
import logging
import os
import sys
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.speech_to_text import SpeechToText
from voice.audio_capture import AudioCapture, PushToTalk
from voice.audio_playback import AudioPlayback
from personality.deva import get_deva_prompt, DEVA_VOICE

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """
    DEVA - Voice-controlled game dev assistant.

    Push-to-talk interface: Hold SPACE to speak, release to send.
    """

    def __init__(
        self,
        push_to_talk_key: str = "space",
        whisper_model: str = "base",
        whisper_device: str = "cuda",
    ):
        """
        Initialize DEVA voice assistant.

        Args:
            push_to_talk_key: Key to hold for recording (default: space)
            whisper_model: Whisper model size (tiny, base, small, medium, large-v3)
            whisper_device: "cuda" for GPU, "cpu" for CPU
        """
        self.push_to_talk_key = push_to_talk_key

        # Components (lazy loaded)
        self._stt: Optional[SpeechToText] = None
        self._capture: Optional[AudioCapture] = None
        self._playback: Optional[AudioPlayback] = None
        self._ptt: Optional[PushToTalk] = None
        self._elevenlabs = None
        self._anthropic = None

        # Settings
        self._whisper_model = whisper_model
        self._whisper_device = whisper_device

        # Conversation history
        self._messages = []

        # State
        self._running = False
        self._processing = False

    def _get_stt(self) -> SpeechToText:
        """Lazy load speech-to-text."""
        if self._stt is None:
            logger.info(f"Loading Whisper model '{self._whisper_model}'...")
            self._stt = SpeechToText(
                model_size=self._whisper_model,
                device=self._whisper_device,
            )
        return self._stt

    def _get_capture(self) -> AudioCapture:
        """Lazy load audio capture."""
        if self._capture is None:
            self._capture = AudioCapture()
        return self._capture

    def _get_playback(self) -> AudioPlayback:
        """Lazy load audio playback."""
        if self._playback is None:
            self._playback = AudioPlayback()
        return self._playback

    def _get_elevenlabs(self):
        """Lazy load ElevenLabs."""
        if self._elevenlabs is None:
            from tools.elevenlabs_tool import ElevenLabsTool
            self._elevenlabs = ElevenLabsTool()
        return self._elevenlabs

    def _get_anthropic(self):
        """Lazy load Anthropic client."""
        if self._anthropic is None:
            try:
                import anthropic
                self._anthropic = anthropic.Anthropic()
            except ImportError:
                raise RuntimeError(
                    "anthropic not installed. Run:\n"
                    "pip install anthropic"
                )
        return self._anthropic

    async def _transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text using Whisper."""
        stt = self._get_stt()
        return stt.transcribe_bytes(audio_data)

    async def _think(self, user_message: str) -> str:
        """Send message to Claude and get DEVA's response."""
        client = self._get_anthropic()

        # Add user message to history
        self._messages.append({
            "role": "user",
            "content": user_message,
        })

        # Get DEVA's system prompt
        system_prompt = get_deva_prompt(mode="voice")

        # Call Claude
        logger.info(f"Thinking about: {user_message[:50]}...")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,  # Keep responses short for voice
            system=system_prompt,
            messages=self._messages,
        )

        # Extract text response
        assistant_message = response.content[0].text

        # Add to history
        self._messages.append({
            "role": "assistant",
            "content": assistant_message,
        })

        # Keep history manageable (last 20 exchanges)
        if len(self._messages) > 40:
            self._messages = self._messages[-40:]

        return assistant_message

    async def _speak(self, text: str):
        """Convert text to speech and play it."""
        elevenlabs = self._get_elevenlabs()
        playback = self._get_playback()

        logger.info(f"DEVA says: {text[:50]}...")

        # Generate audio
        audio_data = await elevenlabs.text_to_speech(
            text=text,
            voice_id=DEVA_VOICE["voice_id"],
            stability=DEVA_VOICE["stability"],
            similarity_boost=DEVA_VOICE["similarity_boost"],
            style=DEVA_VOICE["style"],
        )

        # Play it
        playback.play_mp3(audio_data, blocking=True)

    async def _process_audio(self, audio_data: bytes):
        """Process recorded audio: transcribe → think → speak."""
        if self._processing:
            logger.warning("Already processing, skipping")
            return

        self._processing = True
        try:
            # 1. Transcribe
            print("\n🎤 Transcribing...")
            user_text = await self._transcribe(audio_data)

            if not user_text.strip():
                print("   (no speech detected)")
                return

            print(f"   You: {user_text}")

            # 2. Think
            print("🧠 DEVA is thinking...")
            response = await self._think(user_text)
            print(f"   DEVA: {response}")

            # 3. Speak
            print("🔊 DEVA is speaking...")
            await self._speak(response)

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            print(f"❌ Error: {e}")
        finally:
            self._processing = False
            print(f"\n[Hold {self.push_to_talk_key.upper()} to speak]")

    def _on_audio_callback(self, audio_data: bytes):
        """Callback when push-to-talk recording completes."""
        # Run async processing in the event loop
        asyncio.run(self._process_audio(audio_data))

    def start(self):
        """Start the voice assistant (blocking)."""
        print("=" * 50)
        print("  DEVA - Developer Expert Virtual Assistant")
        print("  (pronounced 'Diva')")
        print("=" * 50)
        print()
        print(f"Hold [{self.push_to_talk_key.upper()}] to speak")
        print("Press [ESC] to quit")
        print()

        # Pre-load Whisper model
        print("Loading speech recognition...")
        self._get_stt()
        print("Ready!\n")

        # Set up push-to-talk
        capture = self._get_capture()
        self._ptt = PushToTalk(capture, key=self.push_to_talk_key)

        self._running = True
        self._ptt.start(self._on_audio_callback)

        # Wait for ESC to quit
        try:
            import keyboard
            keyboard.wait("esc")
        except KeyboardInterrupt:
            pass

        self.stop()

    def stop(self):
        """Stop the voice assistant."""
        self._running = False
        if self._ptt:
            self._ptt.stop()
        print("\nDEVA signing off. You're welcome.")

    async def say(self, text: str):
        """Make DEVA say something (for testing)."""
        await self._speak(text)

    async def ask(self, question: str) -> str:
        """Ask DEVA something and get text response (for testing)."""
        return await self._think(question)


def main():
    """Run DEVA voice assistant."""
    import argparse
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    parser = argparse.ArgumentParser(description="DEVA Voice Assistant")
    parser.add_argument(
        "--key", default="space",
        help="Push-to-talk key (default: space)"
    )
    parser.add_argument(
        "--model", default="base",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Use CPU instead of GPU for Whisper"
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Create and start assistant
    assistant = VoiceAssistant(
        push_to_talk_key=args.key,
        whisper_model=args.model,
        whisper_device="cpu" if args.cpu else "cuda",
    )

    assistant.start()


if __name__ == "__main__":
    main()
