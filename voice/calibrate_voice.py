"""
Voice Calibration for DEVA.

Read the displayed text aloud to help DEVA learn your speech patterns.
This creates a voice profile that improves recognition accuracy.

Run: python voice/calibrate_voice.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Calibration text - contains common words and DEVA-specific terms
CALIBRATION_PARAGRAPHS = [
    """Hello DEVA, this is a calibration test. I'm going to read some text
so you can learn how I speak. My name is the user and I'm working on
game development with Unity and Unreal Engine.""",

    """DEVA stands for Developer Expert Virtual Assistant. She helps with
coding, debugging, and game development. DEVA is pronounced like diva
because she has personality.""",

    """Common commands include: Hey DEVA, thanks DEVA, good job DEVA,
quit, exit, help me with this bug, what do you think, can you fix this,
show me the code.""",

    """Game development terms: shader, prefab, script, component,
rigidbody, collider, animator, spawn point, player controller,
network sync, Photon, multiplayer.""",
]


def main():
    print("=" * 60)
    print("  DEVA Voice Calibration")
    print("  Read the text aloud to improve speech recognition")
    print("=" * 60)
    print()

    # Import after __name__ check for Windows
    from RealtimeSTT import AudioToTextRecorder

    print("Loading speech recognition...")
    recorder = AudioToTextRecorder(
        model="small",
        language="en",
        silero_sensitivity=0.4,
        webrtc_sensitivity=3,
        post_speech_silence_duration=1.0,  # Longer pause for reading
        min_length_of_recording=1.0,
        spinner=False,
        level=50
    )
    print("Ready!\n")

    all_transcriptions = []
    corrections = {}

    for i, paragraph in enumerate(CALIBRATION_PARAGRAPHS, 1):
        print(f"\n{'='*60}")
        print(f"PARAGRAPH {i} of {len(CALIBRATION_PARAGRAPHS)}")
        print("="*60)
        print()
        print("READ THIS TEXT ALOUD:")
        print("-" * 40)
        print(paragraph)
        print("-" * 40)
        print()

        input("Press ENTER when ready to read, then speak clearly...")
        print("\n[Recording... read the text above]")

        # Record
        transcription = recorder.text()

        print(f"\n[What DEVA heard]:")
        print(transcription)
        print()

        all_transcriptions.append(transcription)

        # Check for DEVA recognition
        expected_deva_count = paragraph.lower().count("deva")
        heard_deva_count = transcription.lower().count("deva")

        if expected_deva_count > 0 and heard_deva_count < expected_deva_count:
            print(f"Note: Expected 'DEVA' {expected_deva_count}x, heard {heard_deva_count}x")
            # Look for common misheard versions
            for mishear in ["steve", "eva", "diva", "deba", "teva", "diva"]:
                if mishear in transcription.lower():
                    count = transcription.lower().count(mishear)
                    print(f"  → '{mishear}' appeared {count}x (might be DEVA)")
                    corrections[mishear] = "DEVA"

        print()
        input("Press ENTER to continue...")

    # Build voice profile
    print("\n" + "="*60)
    print("CALIBRATION COMPLETE")
    print("="*60)

    # Combine all transcriptions as context
    combined_context = " ".join(all_transcriptions)

    # Create voice profile
    profile = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "transcriptions": all_transcriptions,
        "combined_context": combined_context,
        "corrections": corrections,
        "initial_prompt": f"The speaker has an Australian accent. Previous speech samples: {combined_context[:500]}"
    }

    # Save profile
    profile_path = os.path.join(os.path.dirname(__file__), "..", "data", "voice_profile.json")
    os.makedirs(os.path.dirname(profile_path), exist_ok=True)

    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=2)

    print(f"\nVoice profile saved to: {profile_path}")
    print(f"\nCorrections detected: {corrections if corrections else 'None'}")
    print(f"\nContext length: {len(combined_context)} characters")
    print("\nDEVA will now use this profile for better recognition.")
    print("Run 'python voice/deva_voice.py' to test!")


if __name__ == "__main__":
    main()
