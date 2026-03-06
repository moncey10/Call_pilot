# call_manager.py - Handles call recordings download from Twilio

import os
import requests
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, RECORDINGS_DIR


def ensure_recordings_dir():
    os.makedirs(RECORDINGS_DIR, exist_ok=True)


def download_recording(recording_sid: str, call_sid: str) -> str:
    """
    Download recording MP3 from Twilio and save locally.
    Returns local file path.
    """
    ensure_recordings_dir()

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    recording = client.recordings(recording_sid).fetch()

    # Twilio recording URL
    recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"

    local_path = os.path.join(RECORDINGS_DIR, f"{call_sid}.mp3")

    # Download the file
    response = requests.get(
        recording_url,
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    )

    with open(local_path, "wb") as f:
        f.write(response.content)

    print(f"[Recording] Saved to {local_path}")
    return local_path


def get_recording_url(recording_sid: str) -> str:
    """Get the public Twilio recording URL."""
    return f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.mp3"