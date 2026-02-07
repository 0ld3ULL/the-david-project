"""
DEVA with ElevenLabs TTS - quality voice with fast response.

Uses ElevenLabs Veronica voice + pygame for ~1 second latency.

Run: python voice/deva_local.py
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import anthropic
import httpx
import pygame
from personality.deva import get_deva_prompt, DEVA_VOICE
from voice.memory import DevaMemory, GroupMemory

# Initialize pygame mixer once
pygame.mixer.init()


class ElevenLabsTTS:
    """ElevenLabs TTS with pygame playback - quality voice, fast start."""

    def __init__(self):
        self.voice_id = DEVA_VOICE["voice_id"]
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.model = DEVA_VOICE.get("model", "eleven_flash_v2_5")
        print(f"Voice: {DEVA_VOICE.get('voice_name', 'Veronica')}")

    def speak(self, text: str):
        """Generate and play speech - ~1 second latency."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        data = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": DEVA_VOICE.get("stability", 0.5),
                "similarity_boost": DEVA_VOICE.get("similarity_boost", 0.75),
            }
        }

        # Download to temp file
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

            # Play with pygame (instant start)
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


def main():
    print("=" * 50)
    print("  DEVA - Developer Expert Virtual Assistant")
    print("  (Type to talk, she speaks back)")
    print("=" * 50)
    print()

    # Initialize
    tts = ElevenLabsTTS()
    client = anthropic.Anthropic()
    base_system_prompt = get_deva_prompt(mode="voice")
    messages = []

    # Memory systems
    print("Loading memory...")
    memory = DevaMemory()
    group_memory = GroupMemory()
    active_engine = memory.get_user("active_engine")
    if active_engine:
        active_engine = active_engine.lower()
        print(f"  Active engine: {active_engine.upper()}")
    print(f"  {memory}")
    print(f"  {group_memory}")

    # Show current engine
    if active_engine:
        print(f"\nEngine: {active_engine.upper()}")
    else:
        print("\nEngine: Not set (type 'switch to Unity/Unreal/Godot')")

    print("\nType and press Enter. Type 'quit' to exit.")
    print()

    def detect_engine(text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["unity", "monobehaviour", "gameobject", "prefab"]):
            return "unity"
        elif any(w in text_lower for w in ["unreal", "blueprint", "actor", "uobject"]):
            return "unreal"
        elif any(w in text_lower for w in ["godot", "gdscript", "node2d", "node3d"]):
            return "godot"
        return "general"

    def is_solution(user_input: str, response: str) -> bool:
        problem_words = ["error", "bug", "issue", "problem", "not working", "crash",
                         "how do i", "how to", "why does", "fix", "help"]
        solution_words = ["you can", "try", "use", "change", "add", "remove",
                          "the issue is", "the problem is", "solution", "fix"]
        has_problem = any(w in user_input.lower() for w in problem_words)
        has_solution = any(w in response.lower() for w in solution_words)
        return has_problem and has_solution and len(response) > 50

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nDEVA: Later.")
                tts.speak("Later.")
                break

            text_lower = user_input.lower()

            # Engine switching
            engine_switch = None
            for eng in ["unity", "unreal", "godot"]:
                if any(phrase in text_lower for phrase in [
                    f"switch to {eng}", f"load {eng}", f"working on {eng}",
                    f"use {eng}", f"{eng} mode", f"{eng} project"
                ]):
                    engine_switch = eng
                    break

            if engine_switch:
                memory.set_user("active_engine", engine_switch.capitalize())
                active_engine = engine_switch
                group_stats = group_memory.get_stats()
                engine_count = group_stats.get("by_engine", {}).get(engine_switch, 0)
                response = f"Switching to {engine_switch.capitalize()} mode. I have {engine_count} {engine_switch.capitalize()} solutions loaded."
                print(f"DEVA: {response}")
                tts.speak(response)
                print(f"[Engine: {engine_switch.upper()}]\n")
                continue

            messages.append({"role": "user", "content": user_input})

            # Build context from memory - use active engine if set
            detected_engine = detect_engine(user_input)
            engine = active_engine if active_engine else detected_engine
            if engine == "general":
                engine = None

            personal_context = memory.get_context(user_input)
            group_context = group_memory.get_context(user_input, engine=engine)

            memory_context = ""
            if personal_context:
                memory_context += personal_context + "\n\n"
            if group_context:
                memory_context += group_context + "\n\n"

            system_prompt = base_system_prompt
            if memory_context:
                system_prompt = f"{memory_context}\n\n{base_system_prompt}"

            # Add engine-specific context
            if active_engine:
                engine_context = {
                    "unity": "Focus on Unity/C# solutions. Use Unity terminology (GameObject, MonoBehaviour, Inspector, Prefab, ScriptableObject).",
                    "unreal": "Focus on Unreal Engine/C++/Blueprint solutions. Use Unreal terminology (Actor, UObject, Blueprint, World, GameMode).",
                    "godot": "Focus on Godot/GDScript solutions. Use Godot terminology (Node, Scene, Signal, Export, Autoload)."
                }
                if active_engine in engine_context:
                    system_prompt += f"\n\n[Active Engine: {active_engine.upper()}]\n{engine_context[active_engine]}"

            system_prompt += "\n\nKeep responses to 1-2 sentences max."

            # Get response from Claude
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=150,
                system=system_prompt,
                messages=messages,
            )

            deva_response = response.content[0].text
            messages.append({"role": "assistant", "content": deva_response})

            # Save solution to group memory if applicable
            if is_solution(user_input, deva_response):
                save_engine = active_engine or detected_engine or "general"
                group_memory.contribute(
                    engine=save_engine,
                    category="general",
                    problem=user_input[:500],
                    solution=deva_response[:1000],
                    contributor_id=memory.get_user("name") or "anonymous"
                )

            print(f"DEVA: {deva_response}")
            tts.speak(deva_response)
            print()

        except KeyboardInterrupt:
            print("\n\nBye.")
            break
        except Exception as e:
            print(f"Error: {e}")

    pygame.mixer.quit()


if __name__ == "__main__":
    main()
