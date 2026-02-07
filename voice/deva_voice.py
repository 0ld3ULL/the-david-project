"""
DEVA with RealtimeSTT - state of the art voice recognition.

Uses RealtimeSTT for instant, accurate speech-to-text.

Run: python voice/deva_voice.py
"""

import glob
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import anthropic
import httpx
import numpy as np
import pygame
from personality.deva import get_deva_prompt, DEVA_VOICE
from voice.memory import DevaMemory, GroupMemory, GameMemory

# Initialize pygame mixer
pygame.mixer.init()


class VoiceAssistant:
    """Voice assistant using RealtimeSTT for instant recognition."""

    def __init__(self):
        print("Initializing DEVA...")

        # Import here after __name__ check (required for Windows multiprocessing)
        from RealtimeSTT import AudioToTextRecorder

        # Configure RealtimeSTT for Australian accent support
        print("  Loading speech recognition (with accent support)...")
        self.recorder = AudioToTextRecorder(
            model="small",                 # Larger model = better accent handling
            language="en",                 # Still English but multilingual model handles accents better
            silero_sensitivity=0.4,        # Voice detection sensitivity
            webrtc_sensitivity=3,          # WebRTC VAD sensitivity (0-3)
            post_speech_silence_duration=0.5,  # Stop after 0.5s silence
            min_length_of_recording=0.3,   # Minimum recording length
            min_gap_between_recordings=0,
            enable_realtime_transcription=False,  # Disable for speed
            spinner=False,
            level=50,  # Reduce logging
            initial_prompt="DEVA is an AI assistant. DEVA is pronounced like diva."  # Help with custom words
        )

        # TTS settings
        self.voice_id = DEVA_VOICE["voice_id"]
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.tts_model = DEVA_VOICE.get("model", "eleven_flash_v2_5")

        # Claude client
        self.client = anthropic.Anthropic()
        self.base_system_prompt = get_deva_prompt(mode="voice")
        self.messages = []

        # Memory systems
        print("  Loading memory...")
        self.memory = DevaMemory()
        self.group_memory = GroupMemory()
        self.game_memory = GameMemory()

        # Load active engine and game
        self.active_engine = self.memory.get_user("active_engine")
        if self.active_engine:
            self.active_engine = self.active_engine.lower()
            print(f"  Active engine: {self.active_engine.upper()}")

        self.active_game = self.memory.get_user("active_game")
        if self.active_game:
            print(f"  Active game: {self.active_game}")

        print(f"  {self.memory}")
        print(f"  {self.group_memory}")
        print(f"  {self.game_memory}")

        print(f"  Voice: {DEVA_VOICE.get('voice_name', 'Veronica')}")

        # Create a beep sound for ready indicator
        self._create_beep()

        print("Ready!")
        print("(First response may take longer as model warms up)\n")

    def _create_beep(self):
        """Create a short beep sound to indicate ready."""
        import numpy as np
        import tempfile
        import wave

        # Generate a short beep (440Hz, 0.1s)
        sample_rate = 22050
        duration = 0.1
        frequency = 880  # Higher pitch beep

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        beep = np.sin(frequency * 2 * np.pi * t) * 0.3
        beep = (beep * 32767).astype(np.int16)

        self.beep_path = tempfile.mktemp(suffix='.wav')
        with wave.open(self.beep_path, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            f.writeframes(beep.tobytes())

    def play_ready_beep(self):
        """Play a beep to indicate ready to listen."""
        try:
            pygame.mixer.music.load(self.beep_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pass
            pygame.mixer.music.unload()
        except:
            pass

    def listen(self) -> str:
        """Listen for speech using RealtimeSTT."""
        self.play_ready_beep()  # Beep when ready
        print("[READY - speak now]")
        text = self.recorder.text()
        return text.strip() if text else ""

    def speak(self, text: str):
        """Generate and play speech via ElevenLabs."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        data = {
            "text": text,
            "model_id": self.tts_model,
            "voice_settings": {
                "stability": DEVA_VOICE.get("stability", 0.5),
                "similarity_boost": DEVA_VOICE.get("similarity_boost", 0.75),
            }
        }

        temp_path = tempfile.mktemp(suffix='.mp3')
        try:
            with httpx.Client(timeout=30) as client:
                with client.stream("POST", url, headers=headers, json=data) as response:
                    if response.status_code != 200:
                        print(f"TTS Error: {response.status_code}")
                        return
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_bytes():
                            f.write(chunk)

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.05)

            pygame.mixer.music.unload()
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def _detect_engine(self, text: str) -> str:
        """Detect which game engine is being discussed."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["unity", "monobehaviour", "gameobject", "prefab"]):
            return "unity"
        elif any(w in text_lower for w in ["unreal", "blueprint", "actor", "uobject"]):
            return "unreal"
        elif any(w in text_lower for w in ["godot", "gdscript", "node2d", "node3d"]):
            return "godot"
        return "general"

    def _is_solution(self, user_input: str, response: str) -> bool:
        """Check if this exchange contains a solution worth saving."""
        # Look for problem indicators in user input
        problem_words = ["error", "bug", "issue", "problem", "not working", "crash",
                         "how do i", "how to", "why does", "fix", "help"]
        has_problem = any(w in user_input.lower() for w in problem_words)

        # Look for solution indicators in response
        solution_words = ["you can", "try", "use", "change", "add", "remove",
                          "the issue is", "the problem is", "solution", "fix"]
        has_solution = any(w in response.lower() for w in solution_words)

        return has_problem and has_solution and len(response) > 50

    def think(self, user_input: str) -> str:
        """Get DEVA's response from Claude with memory context."""
        self.messages.append({"role": "user", "content": user_input})

        # Use active engine if set, otherwise auto-detect
        detected_engine = self._detect_engine(user_input)
        engine = self.active_engine if self.active_engine else detected_engine
        if engine == "general":
            engine = None

        # Build context from all memory systems
        personal_context = self.memory.get_context(user_input)
        group_context = self.group_memory.get_context(user_input, engine=engine)
        game_context = self.game_memory.get_context(self.active_game) if self.active_game else ""

        memory_context = ""
        if game_context:
            memory_context += game_context + "\n\n"
        if personal_context:
            memory_context += personal_context + "\n\n"
        if group_context:
            memory_context += group_context + "\n\n"

        # Build system prompt with memory and engine context
        system_prompt = self.base_system_prompt
        if memory_context:
            system_prompt = f"{memory_context}\n\n{self.base_system_prompt}"

        # Add engine-specific context when active
        if self.active_engine:
            engine_context = {
                "unity": "Focus on Unity/C# solutions. Use Unity terminology (GameObject, MonoBehaviour, Inspector, Prefab, ScriptableObject).",
                "unreal": "Focus on Unreal Engine/C++/Blueprint solutions. Use Unreal terminology (Actor, UObject, Blueprint, World, GameMode).",
                "godot": "Focus on Godot/GDScript solutions. Use Godot terminology (Node, Scene, Signal, Export, Autoload)."
            }
            if self.active_engine in engine_context:
                system_prompt += f"\n\n[Active Engine: {self.active_engine.upper()}]\n{engine_context[self.active_engine]}"

        system_prompt += "\n\nKeep responses to 1-2 sentences max."

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            system=system_prompt,
            messages=self.messages,
        )

        deva_response = response.content[0].text
        self.messages.append({"role": "assistant", "content": deva_response})

        # Check if this is a solution worth saving
        if self._is_solution(user_input, deva_response):
            save_engine = self.active_engine or detected_engine or "general"

            # Save to Group Memory (ALL DEVS)
            self.group_memory.contribute(
                engine=save_engine,
                category="general",
                problem=user_input[:500],
                solution=deva_response[:1000],
                contributor_id=self.memory.get_user("name") or "anonymous"
            )

            # Also save to Game Memory if a game is active
            if self.active_game:
                self.game_memory.add_bug(
                    game_name=self.active_game,
                    bug_description=user_input[:500],
                    solution=deva_response[:1000],
                    root_cause=None,  # Could extract this with more sophisticated parsing
                    prevention=None
                )

        return deva_response


def main():
    print("=" * 50)
    print("  DEVA - Voice Assistant (RealtimeSTT)")
    print("=" * 50)

    assistant = VoiceAssistant()

    # Show current engine and game
    if assistant.active_game:
        game = assistant.game_memory.get_game(assistant.active_game)
        print(f"Game: {assistant.active_game} ({game['engine'].upper() if game else 'unknown'})")
    elif assistant.active_engine:
        print(f"Engine: {assistant.active_engine.upper()} (no game selected)")
    else:
        print("No engine/game set. Say 'switch to Unity' or 'working on [game name]'")

    print("\nJust start speaking. Say 'quit' to exit.")
    print("Ctrl+C to force quit.\n")

    while True:
        try:
            # Listen
            t1 = time.time()
            user_text = assistant.listen()
            stt_time = time.time() - t1

            if not user_text:
                continue

            print(f"You: {user_text} [{stt_time:.1f}s]")

            # Check for quit
            if any(word in user_text.lower() for word in ['quit', 'exit', 'goodbye', 'bye']):
                print("\nDEVA: Later.")
                assistant.speak("Later.")
                break

            # Check for memory commands
            text_lower = user_text.lower()

            # "My name is X"
            if "my name is" in text_lower:
                import re
                match = re.search(r"my name is (\w+)", text_lower)
                if match:
                    name = match.group(1).capitalize()
                    assistant.memory.set_user("name", name)
                    response = f"Got it, {name}. I'll remember that."
                    print(f"DEVA: {response}")
                    assistant.speak(response)
                    continue

            # Engine switching - "Switch to Unity/Unreal/Godot" or "I'm working on Unity"
            engine_switch = None
            for engine in ["unity", "unreal", "godot"]:
                if any(phrase in text_lower for phrase in [
                    f"switch to {engine}",
                    f"switching to {engine}",
                    f"load {engine}",
                    f"working on {engine}",
                    f"working in {engine}",
                    f"i'm on {engine}",
                    f"im on {engine}",
                    f"use {engine}",
                    f"using {engine} now",
                    f"{engine} mode",
                    f"{engine} project"
                ]):
                    engine_switch = engine
                    break

            if engine_switch:
                assistant.memory.set_user("active_engine", engine_switch.capitalize())
                assistant.active_engine = engine_switch

                # Get engine-specific stats
                group_stats = assistant.group_memory.get_stats()
                engine_count = group_stats.get("by_engine", {}).get(engine_switch, 0)

                response = f"Switching to {engine_switch.capitalize()} mode. I have {engine_count} {engine_switch.capitalize()} solutions loaded."
                print(f"DEVA: {response}")
                assistant.speak(response)
                print(f"[Engine: {engine_switch.upper()}]")
                continue

            # "What engine" or "Current engine"
            if any(phrase in text_lower for phrase in ["what engine", "which engine", "current engine", "what mode"]):
                current = assistant.memory.get_user("active_engine") or "None set"
                response = f"I'm currently in {current} mode."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # Game switching - "Working on Stavin Martian" or "Switch to Stavin Martian"
            game_switch_phrases = ["working on", "switch to game", "load game", "open project"]
            for phrase in game_switch_phrases:
                if phrase in text_lower:
                    # Extract game name after the phrase
                    import re
                    pattern = rf"{phrase}\s+(.+?)(?:\s+game|\s+project)?$"
                    match = re.search(pattern, text_lower)
                    if match:
                        game_name = match.group(1).strip().title()
                        game = assistant.game_memory.get_game(game_name)

                        if game:
                            assistant.active_game = game_name
                            assistant.memory.set_user("active_game", game_name)
                            # Also set engine from game
                            assistant.active_engine = game["engine"]
                            assistant.memory.set_user("active_engine", game["engine"].capitalize())

                            stats = assistant.game_memory.get_stats()
                            systems = assistant.game_memory.get_systems(game_name)
                            bugs = assistant.game_memory.get_bugs(game_name)

                            response = f"Loaded {game_name}. {game['engine'].capitalize()} project with {len(systems)} systems and {len(bugs)} solved bugs in memory."
                            print(f"DEVA: {response}")
                            assistant.speak(response)
                            print(f"[Game: {game_name} | Engine: {game['engine'].upper()}]")
                        else:
                            response = f"I don't have {game_name} registered. Say 'register game {game_name}' to add it."
                            print(f"DEVA: {response}")
                            assistant.speak(response)
                        break
            else:
                # Continue to next check if no game switch matched
                pass

            # Register new game - "Register game Stavin Martian"
            if "register game" in text_lower:
                import re
                match = re.search(r"register game\s+(.+?)(?:\s+as\s+(\w+))?$", text_lower)
                if match:
                    game_name = match.group(1).strip().title()
                    engine = match.group(2) if match.group(2) else assistant.active_engine or "unity"

                    assistant.game_memory.register_game(game_name, engine)
                    assistant.active_game = game_name
                    assistant.memory.set_user("active_game", game_name)

                    response = f"Registered {game_name} as a {engine.capitalize()} project. I'll remember everything we work on."
                    print(f"DEVA: {response}")
                    assistant.speak(response)
                    print(f"[Game: {game_name} | Engine: {engine.upper()}]")
                    continue

            # List games - "What games do you know" or "List games"
            if any(phrase in text_lower for phrase in ["list games", "what games", "which games", "show games"]):
                games = assistant.game_memory.list_games()
                if games:
                    game_list = ", ".join(f"{g['name']} ({g['engine']})" for g in games)
                    response = f"I know {len(games)} games: {game_list}."
                else:
                    response = "No games registered yet. Say 'register game' followed by the name."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # What game - "What game" or "Current project"
            if any(phrase in text_lower for phrase in ["what game", "which game", "current project", "current game"]):
                current = assistant.active_game or "None"
                if current != "None":
                    game = assistant.game_memory.get_game(current)
                    response = f"Working on {current}, a {game['engine'].capitalize()} project."
                else:
                    response = "No game selected. Say 'working on' followed by the game name."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # Game info - "Tell me about this game" or "Game info"
            if any(phrase in text_lower for phrase in ["game info", "about this game", "project info"]):
                if assistant.active_game:
                    context = assistant.game_memory.get_context(assistant.active_game)
                    print(f"\n{context}\n")
                    response = f"Showing {assistant.active_game} info on screen."
                else:
                    response = "No game selected."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # "Memory stats" or "what do you know"
            if "memory" in text_lower and ("stats" in text_lower or "status" in text_lower):
                stats = assistant.memory.get_stats()
                group_stats = assistant.group_memory.get_stats()
                game_stats = assistant.game_memory.get_stats()
                current_engine = assistant.memory.get_user("active_engine") or "None"
                by_engine = group_stats.get("by_engine", {})
                engine_breakdown = ", ".join(f"{k}: {v}" for k, v in by_engine.items()) if by_engine else "empty"
                response = f"Active engine: {current_engine}. Group: {group_stats['total_solutions']} solutions. Games: {game_stats['games']} with {game_stats['bugs']} solved bugs."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # Export knowledge - "Export knowledge" or "Share knowledge"
            if any(phrase in text_lower for phrase in ["export knowledge", "share knowledge", "export solutions", "sync out"]):
                # Export group knowledge
                group_path = assistant.group_memory.export_solutions()
                print(f"Exported group knowledge to: {group_path}")

                # Export current game if active
                if assistant.active_game:
                    game_path = assistant.game_memory.export_game(assistant.active_game)
                    print(f"Exported {assistant.active_game} to: {game_path}")
                    response = f"Exported group knowledge and {assistant.active_game} game data. Share these files with other devs."
                else:
                    response = "Exported group knowledge. Share the file with other devs."

                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # Import knowledge - "Import knowledge"
            if any(phrase in text_lower for phrase in ["import knowledge", "sync in", "load shared"]):
                import glob
                data_dir = os.path.dirname(assistant.group_memory.db_path)

                # Look for export files
                group_exports = glob.glob(os.path.join(data_dir, "group_knowledge_export*.json"))
                game_exports = glob.glob(os.path.join(data_dir, "game_*_export.json"))

                imported = []

                for gf in group_exports:
                    result = assistant.group_memory.import_solutions(gf)
                    imported.append(f"group: +{result['added']}")
                    print(f"Imported {result['added']} solutions from {gf}")

                for gf in game_exports:
                    result = assistant.game_memory.import_game(gf)
                    imported.append(f"{result['game']}: +{result['imported']['bugs']} bugs")
                    print(f"Imported {result['game']} game data")

                if imported:
                    response = f"Imported: {', '.join(imported)}."
                else:
                    response = "No export files found in data folder."

                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # Think
            t2 = time.time()
            response = assistant.think(user_text)
            think_time = time.time() - t2

            # Speak
            print(f"DEVA: {response}")
            t3 = time.time()
            assistant.speak(response)
            speak_time = time.time() - t3

            print(f"[STT:{stt_time:.1f}s Claude:{think_time:.1f}s TTS:{speak_time:.1f}s]\n")

        except KeyboardInterrupt:
            print("\n\nBye.")
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    pygame.mixer.quit()


if __name__ == "__main__":
    main()
