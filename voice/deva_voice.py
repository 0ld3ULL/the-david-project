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
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import anthropic
import httpx
import numpy as np
import pygame
from personality.deva import get_deva_prompt, DEVA_VOICE
from voice.memory import DevaMemory, GroupMemory, GameMemory
from voice.wall_mode import WallCollector, CONTEXT_LIMITS
from voice.gemini_client import GeminiClient, GeminiResponse
from voice.tools.tool_executor import ToolExecutor, ToolExecutorConfig, ConsoleLogWatcher

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
            silero_sensitivity=0.2,        # Lower = harder to trigger (was 0.4)
            webrtc_sensitivity=3,          # WebRTC VAD sensitivity (0-3, 3 = least sensitive)
            post_speech_silence_duration=0.8,  # Wait longer for pause (was 0.5)
            min_length_of_recording=1.0,   # Ignore anything under 1 second (was 0.3)
            min_gap_between_recordings=0.5, # Brief cooldown between recordings (was 0)
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
        self._conversation_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "conversation_history.json"
        )
        self._load_conversation()

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

        # Wall Mode - project path and Gemini client
        self.project_path = self.memory.get_user("project_path")
        if self.project_path:
            print(f"  Project path: {self.project_path}")
        self.wall_context = None  # Cached wall context for analysis
        self.wall_collector = None  # WallCollector instance

        # Initialize Gemini client for wall mode (optional - only if API key exists)
        try:
            self.gemini = GeminiClient()
            print(f"  Gemini: {self.gemini.provider} API ready")
        except ValueError:
            self.gemini = None
            print("  Gemini: No API key (wall mode will use Claude)")

        # Initialize Tool Executor for code editing
        print("  Loading tools...")
        tool_config = ToolExecutorConfig(
            allowed_roots=[self.project_path] if self.project_path else [],
            max_tool_calls=15,
            require_confirmation=False  # DEVA can edit freely
        )
        self.tool_executor = ToolExecutor(tool_config)
        self.tools_enabled = True  # Toggle with "tools on/off"
        self._last_full_response = None  # Full response for console (tool mode)
        print(f"  Tools: {len(self.tool_executor.tools)} available")

        # Check Unity MCP connection (non-blocking — just tries once)
        if self.tool_executor.unity_bridge.is_connected:
            print(f"  Unity MCP: Connected ({self.tool_executor.unity_bridge._base_url})")
        else:
            print(f"  Unity MCP: Not connected (will auto-detect when available)")

        # Console Log Watcher for Unity feedback
        self.log_watcher = ConsoleLogWatcher()
        self._setup_log_watcher()
        print(f"  Logs: {len(self.log_watcher.log_paths)} watched")

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

    def _load_conversation(self):
        """Load previous conversation history so DEVA remembers what was discussed."""
        try:
            if os.path.exists(self._conversation_file):
                import json
                from datetime import datetime
                with open(self._conversation_file, 'r') as f:
                    data = json.load(f)
                # Load last 20 exchanges (40 messages) to keep context manageable
                self.messages = data.get("messages", [])[-40:]
                if self.messages:
                    # Work out how long it's been since last conversation
                    last_ts = None
                    for msg in reversed(self.messages):
                        if msg["role"] == "user" and msg["content"].startswith("["):
                            try:
                                ts_str = msg["content"][1:msg["content"].index("]")]
                                last_ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
                                break
                            except (ValueError, IndexError):
                                pass

                    time_gap = ""
                    if last_ts:
                        diff = datetime.now() - last_ts
                        if diff.days > 0:
                            time_gap = f" (last spoke {diff.days} day{'s' if diff.days != 1 else ''} ago)"
                        elif diff.seconds > 3600:
                            hours = diff.seconds // 3600
                            time_gap = f" (last spoke {hours} hour{'s' if hours != 1 else ''} ago)"
                        elif diff.seconds > 60:
                            mins = diff.seconds // 60
                            time_gap = f" (last spoke {mins} min ago)"
                        else:
                            time_gap = " (just now)"

                    print(f"  Conversation: {len(self.messages)//2} recent exchanges loaded{time_gap}")

                    # Inject a system-style note so DEVA knows the time context
                    if time_gap and last_ts:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        gap_note = f"[{now_str}] [SESSION START - It is now {now_str}. Our last conversation was at {last_ts.strftime('%Y-%m-%d %H:%M')}{time_gap}. Pick up where we left off naturally.]"
                        self.messages.append({"role": "user", "content": gap_note})
                        self.messages.append({"role": "assistant", "content": "Got it, I remember our conversation. What's up?"})
        except Exception as e:
            print(f"  Conversation: could not load ({e})")
            self.messages = []

    def _save_conversation(self):
        """Save conversation history to disk so DEVA remembers between restarts."""
        try:
            import json
            os.makedirs(os.path.dirname(self._conversation_file), exist_ok=True)
            # Keep last 50 exchanges (100 messages) - older ones fade like real memory
            data = {
                "messages": self.messages[-100:]
            }
            with open(self._conversation_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Don't crash if save fails

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

    def _setup_log_watcher(self):
        """Set up log file watching for Unity editor and production builds."""
        # Auto-discover logs based on project path
        added = self.log_watcher.auto_discover_logs(self.project_path)

        # Project console log (if using console redirect)
        if self.project_path:
            project_console = os.path.join(os.path.dirname(self.project_path), "console_log.txt")
            self.log_watcher.add_log_path(project_console)

        # Known PLAYA3ULL GAMES projects
        locallow = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow")
        if os.path.exists(locallow):
            known_projects = [
                ("PLAYA3ULL GAMES", "Amphitheatre"),
                ("PLAYA3ULL GAMES", "AMPHI-Island"),
            ]
            for company, product in known_projects:
                player_log = os.path.join(locallow, company, product, "Player.log")
                self.log_watcher.add_log_path(player_log)
                output_log = os.path.join(locallow, company, product, "output_log.txt")
                self.log_watcher.add_log_path(output_log)

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

    def _needs_tools(self, text: str) -> bool:
        """Detect if the user's request requires tool use.

        Uses explicit trigger words rather than guessing from conversation.
        The user says a trigger word (e.g. 'program') when they're ready
        for DEVA to take action. Everything else is normal conversation.
        """
        if not self.tools_enabled:
            return False
        text_lower = text.lower().strip()

        # Explicit trigger phrases - clear, deliberate commands
        # Normal conversation never accidentally triggers these
        trigger_phrases = [
            "execute program",      # Primary trigger: "DEVA, execute program"
            "deva execute",         # Alternate phrasing
        ]
        return any(trigger in text_lower for trigger in trigger_phrases)

    def _extract_spoken_text(self, response: str) -> tuple[str, str]:
        """
        Extract spoken text from response. Claude wraps what should be
        spoken aloud in [SAY]...[/SAY] tags. Everything else is internal.

        Returns:
            Tuple of (spoken_text, full_text_for_console)
        """
        import re
        # Find all [SAY]...[/SAY] blocks
        say_blocks = re.findall(r'\[SAY\](.*?)\[/SAY\]', response, re.DOTALL)
        if say_blocks:
            spoken = " ".join(block.strip() for block in say_blocks)
            return spoken, response
        else:
            # No [SAY] tags in a tool response = Claude forgot to tag
            # Don't speak internal tool narration - just say "Done."
            return "", response

    def think_with_tools(self, user_input: str) -> str:
        """Get DEVA's response using tools to modify code."""
        # Build system prompt with tool context
        system_prompt = self.base_system_prompt + """

YOU HAVE TOOLS. The developer has said "Execute Program" which means GO.
Review the conversation history to understand what needs to be done.
If the task is clear, DO IT immediately with your tools.
If you're unsure what exactly to do, ask ONE short clarifying question in [SAY] tags
before acting. Don't guess - clarify.

== COMMON TASKS ==

OPEN UNITY:
- run_command: "start Unity" (Windows)
- run_command: "Unity -projectPath <path>"

BUILD PROJECT:
- Unity: run_command "dotnet build" or use Unity command line
- Unreal: run_command "UnrealEditor"

FIX/EDIT CODE:
1. search_code or read_file to find the code
2. edit_file to make precise changes
3. Tell them what you changed

GIT OPERATIONS:
- git_status, git_diff, git_commit

== PROJECT ==
Path: """ + (self.project_path or "Not set") + """
OS: Windows

== OUTPUT FORMAT ==
CRITICAL: Wrap ONLY what should be SPOKEN ALOUD in [SAY]...[/SAY] tags.
Everything outside these tags is internal and will only show on screen.

Example good response:
  Reading the file... Found the issue on line 342.
  [SAY]Fixed it. Line 342 had the collider disabled but never re-enabled.[/SAY]

Example bad response (DON'T do this):
  [SAY]I'm going to read the file now. Let me search for the collider code. OK I found it on line 342. The issue is that the collider gets disabled but never re-enabled. I'll edit the file now. Done, I've fixed it.[/SAY]

Keep spoken output to 1-2 sentences. Just the result, not the process.

== RULES ==
- Don't say "I can't" - USE YOUR TOOLS
- Make the change, then report what you did
- Be direct. One sentence spoken if possible.
- NEVER narrate your tool actions in [SAY] tags."""

        # Add wall context if available
        if self.wall_context:
            system_prompt += f"\n\n[CODEBASE CONTEXT - {len(self.wall_context)} chars loaded]\n"
            system_prompt += "You have the codebase in context. Reference specific files and line numbers."

        # Build messages WITH conversation history so DEVA knows what was discussed
        # When user says "Program", DEVA needs the prior conversation for context
        messages = list(self.messages)  # Copy existing conversation
        messages.append({"role": "user", "content": user_input})

        # Check for new log content
        new_logs = self.log_watcher.check_for_new_content()
        if new_logs:
            log_context = "\n\n[CONSOLE LOG UPDATE]\n"
            for path, content in new_logs.items():
                log_name = os.path.basename(path)
                # Only include last 50 lines
                lines = content.strip().split("\n")[-50:]
                log_context += f"\n--- {log_name} ---\n" + "\n".join(lines)
            messages[0]["content"] = user_input + log_context

        try:
            # Run with tools
            response_text, updated_messages = self.tool_executor.run_with_tools(
                client=self.client,
                messages=messages,
                system_prompt=system_prompt,
                model="claude-opus-4-20250514",
                max_tokens=4096
            )

            # Add to conversation history with timestamp
            from datetime import datetime
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.messages.append({"role": "user", "content": f"[{ts}] {user_input}"})
            self.messages.append({"role": "assistant", "content": response_text})
            self._save_conversation()

            # Extract spoken part vs console-only part
            spoken, full = self._extract_spoken_text(response_text)
            # Store full text for console, return spoken text for TTS
            self._last_full_response = full
            # If no [SAY] tags were found, say "Done" rather than nothing
            return spoken if spoken else "Done."

        except Exception as e:
            return f"Tool error: {str(e)}"

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
        # Check if this needs tools (code editing, commands)
        if self._needs_tools(user_input):
            return self.think_with_tools(user_input)

        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.messages.append({"role": "user", "content": f"[{ts}] {user_input}"})

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

        # WALL MODE: If wall context is loaded, use Gemini for analysis
        if self.wall_context and self.gemini:
            # Use Gemini for wall mode (800K context vs Claude's 200K)
            try:
                gemini_response = self.gemini.analyze(self.wall_context, user_input)
                deva_response = gemini_response.text
                self.messages.append({"role": "assistant", "content": deva_response})
                self._save_conversation()
                return deva_response
            except Exception as e:
                # Fall back to Claude without wall context
                print(f"[Gemini error: {e}, falling back to Claude]")
                self.wall_context = None  # Clear broken wall context

        # Add engine-specific context when active
        if self.active_engine:
            engine_context = {
                "unity": "Focus on Unity/C# solutions. Use Unity terminology (GameObject, MonoBehaviour, Inspector, Prefab, ScriptableObject).",
                "unreal": "Focus on Unreal Engine/C++/Blueprint solutions. Use Unreal terminology (Actor, UObject, Blueprint, World, GameMode).",
                "godot": "Focus on Godot/GDScript solutions. Use Godot terminology (Node, Scene, Signal, Export, Autoload)."
            }
            if self.active_engine in engine_context:
                system_prompt += f"\n\n[Active Engine: {self.active_engine.upper()}]\n{engine_context[self.active_engine]}"

        # Adjust max tokens based on wall mode
        if self.wall_context:
            # Wall mode needs detailed responses
            max_response_tokens = 4096
            system_prompt += "\n\nBe specific about file paths and line numbers."
        else:
            max_response_tokens = 4096

        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=max_response_tokens,
            system=system_prompt,
            messages=self.messages,
        )

        deva_response = response.content[0].text
        self.messages.append({"role": "assistant", "content": deva_response})
        self._save_conversation()

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

            # ==================== WALL MODE ====================
            # "Set project path" or "Project is at"
            if any(phrase in text_lower for phrase in ["set project", "project path", "project is at", "project folder", "project is"]):
                import re
                # Try to extract path from speech
                # Support both D: (main PC) and C: (David's laptop) drives
                project = None

                if "amphitheatre" in text_lower:
                    # Check both drives
                    candidates = [
                        r"D:\Games\PLAYA3ULL GAMES games\Amphitheatre\Amphitheatre",
                        r"C:\Games\Amphitheatre\Amphitheatre",
                    ]
                    for p in candidates:
                        if os.path.exists(p):
                            project = p
                            break
                elif "amphi" in text_lower and "island" in text_lower:
                    candidates = [
                        r"D:\Games\PLAYA3ULL GAMES games\AMPHI-Island",
                        r"C:\Games\AMPHI-Island",
                    ]
                    for p in candidates:
                        if os.path.exists(p):
                            project = p
                            break

                # Also try to parse explicit path from speech like "C Games Amphitheatre"
                if not project:
                    # Convert speech to path: "c games amphitheatre" -> "C:\Games\Amphitheatre"
                    path_match = re.search(r"([cde])\s*(?:drive|colon)?\s*(.+)", text_lower)
                    if path_match:
                        drive = path_match.group(1).upper()
                        parts = path_match.group(2).strip().split()
                        # Join with backslash
                        potential_path = drive + ":\\" + "\\".join(p.capitalize() for p in parts)
                        if os.path.exists(potential_path):
                            project = potential_path

                if not project:
                    response = "I need a project path. Say 'project is Amphitheatre' or give me the path."
                    print(f"DEVA: {response}")
                    assistant.speak(response)
                    continue

                if os.path.exists(project):
                    assistant.project_path = project
                    assistant.memory.set_user("project_path", project)
                    # Update tool executor allowed paths
                    assistant.tool_executor.config.allowed_roots = [project]
                    assistant.tool_executor.file_tools.allowed_roots = [project]
                    assistant.tool_executor.command_tools.allowed_directories = [project]
                    # Update log watcher
                    assistant._setup_log_watcher()
                    response = f"Got it - {os.path.basename(project)}. What's up with your project files?"
                    print(f"[Project: {project}]")
                else:
                    response = f"Path not found: {project}"
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # "Wall [subsystem]" or "Wall mode" - Load codebase into context
            if text_lower.startswith("wall ") or text_lower == "wall" or "wall mode" in text_lower:
                if not assistant.project_path:
                    response = "No project path set. Say 'project is Amphitheatre' first."
                    print(f"DEVA: {response}")
                    assistant.speak(response)
                    continue

                # Parse wall command
                import re
                subsystem = None
                query = None

                # "wall voice" -> subsystem filter
                # "wall player falls through floor" -> query filter
                # "wall" -> full project
                if text_lower.startswith("wall "):
                    arg = text_lower[5:].strip()
                    # Check if it's a known subsystem
                    known_subsystems = ["voice", "networking", "player", "seating", "ui",
                                       "camera", "animation", "rendering", "physics", "events"]
                    if arg in known_subsystems:
                        subsystem = arg
                    elif arg and arg != "mode":
                        query = arg

                try:
                    print(f"\n[WALL MODE: Loading {subsystem or query or 'full project'}...]")
                    collector = WallCollector(assistant.project_path, engine=assistant.active_engine or "unity")

                    t_wall = time.time()
                    result = collector.collect(subsystem=subsystem, query=query)
                    wall_time = time.time() - t_wall

                    # Cache the context for subsequent questions
                    assistant.wall_context = result.context_text

                    print(f"[WALL LOADED: {result.total_files} files, {result.total_tokens:,} tokens, {wall_time:.1f}s]")

                    # Show subsystem breakdown
                    if not subsystem and not query:
                        summary = collector.get_subsystem_summary()
                        print("\nSubsystems found:")
                        for sub, count in list(summary.items())[:5]:
                            print(f"  {sub}: {count} files")

                    response = f"Wall loaded. {result.total_files} files, {result.total_tokens:,} tokens. Ask me anything about the code."
                    print(f"\nDEVA: {response}")
                    assistant.speak(response)

                except Exception as e:
                    response = f"Wall mode error: {str(e)}"
                    print(f"DEVA: {response}")
                    assistant.speak(response)
                continue

            # "Clear wall" - Clear wall context
            if "clear wall" in text_lower:
                assistant.wall_context = None
                response = "Wall context cleared."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # ==================== UNITY MCP ====================
            # "Unity connect" / "Unity status" / "Unity disconnect"
            if any(phrase in text_lower for phrase in ["unity connect", "connect to unity", "connect unity"]):
                assistant.tool_executor.unity_bridge.invalidate_cache()
                status = assistant.tool_executor.unity_bridge.get_status()
                if assistant.tool_executor.unity_bridge.is_connected:
                    response = "Connected to Unity. I can now control the editor directly."
                else:
                    response = "Can't reach Unity MCP server. Make sure Unity is open with the MCP plugin running on port 8080."
                print(f"[Unity: {status}]")
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            if any(phrase in text_lower for phrase in ["unity status", "unity connection", "is unity connected"]):
                status = assistant.tool_executor.unity_bridge.get_status()
                connected = assistant.tool_executor.unity_bridge.is_connected
                if connected:
                    response = "Unity is connected. All 10 editor tools are available."
                else:
                    response = "Unity is not connected. Say 'unity connect' after opening Unity with the MCP plugin."
                print(f"[Unity: {status}]")
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            if any(phrase in text_lower for phrase in ["unity disconnect", "disconnect unity"]):
                assistant.tool_executor.unity_bridge._health_ok = False
                assistant.tool_executor.unity_bridge._health_checked_at = time.time() + 9999
                response = "Disconnected from Unity. Editor tools disabled."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # ==================== TOOLS MODE ====================
            # "Tools on/off" - Toggle tool capabilities
            if "tools on" in text_lower or "enable tools" in text_lower:
                assistant.tools_enabled = True
                response = "Tools enabled. I can now edit code directly."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            if "tools off" in text_lower or "disable tools" in text_lower:
                assistant.tools_enabled = False
                response = "Tools disabled. I'll only analyze and advise."
                print(f"DEVA: {response}")
                assistant.speak(response)
                continue

            # "What tools" or "Tool status"
            if any(phrase in text_lower for phrase in ["what tools", "tool status", "tools status", "list tools"]):
                status = "enabled" if assistant.tools_enabled else "disabled"
                tool_count = len(assistant.tool_executor.tools)
                exec_count = len(assistant.tool_executor.execution_history)
                response = f"Tools are {status}. {tool_count} tools available, {exec_count} operations this session."
                print(f"DEVA: {response}")
                # Print tool list
                print("  Available: " + ", ".join(assistant.tool_executor.tools.keys()))
                assistant.speak(response)
                continue

            # "Check logs" or "Any errors"
            if any(phrase in text_lower for phrase in ["check logs", "check console", "any errors", "show errors", "what errors"]):
                new_content = assistant.log_watcher.check_for_new_content()
                if new_content:
                    print("\n[LOG UPDATES]")
                    for path, content in new_content.items():
                        print(f"\n--- {os.path.basename(path)} ---")
                        # Show last 20 lines
                        lines = content.strip().split("\n")[-20:]
                        print("\n".join(lines))

                    # Check for errors
                    has_errors = any(
                        "error" in content.lower() or "exception" in content.lower()
                        for content in new_content.values()
                    )
                    if has_errors:
                        response = "Found new errors in the logs. Showing on screen."
                    else:
                        response = "New log content, no errors detected."
                else:
                    response = "No new log content since last check."
                print(f"\nDEVA: {response}")
                assistant.speak(response)
                continue

            # "Watch log [path]" - Add custom log path
            if "watch log" in text_lower or "add log" in text_lower:
                # Try to extract a path - this is tricky with voice
                response = "To watch a custom log, I need the file path. What's the full path to the log file?"
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
            assistant._last_full_response = None
            response = assistant.think(user_text)
            think_time = time.time() - t2

            # Show full response on console (includes internal tool narration)
            full_response = assistant._last_full_response or response
            if full_response != response:
                # Tool mode: show full text on console, speak only the [SAY] part
                # Strip [SAY] tags for clean console output
                console_text = full_response.replace("[SAY]", "").replace("[/SAY]", "")
                print(f"DEVA: {console_text}")
                print(f"[Speaking: {response}]")
            else:
                print(f"DEVA: {response}")

            # Speak (only the spoken part)
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
