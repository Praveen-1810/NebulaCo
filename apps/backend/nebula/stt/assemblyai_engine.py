import os
import time
import requests
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from tempfile import NamedTemporaryFile

from nebula.logger import get_logger

logger = get_logger("AssemblyAI")

MIC_DEVICE_INDEX = 1  # Your internal mic index

ASSEMBLYAI_API_KEY = "70444a4d0df9474091061f4aa3594d9c"


class AssemblyAIEngine:

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }

    # =========================================================
    # 🔥 Silence-based smart recording
    # =========================================================
    def record_audio(self):

        logger.info("Listening (silence-based)...")

        threshold = 500        # volume sensitivity
        silence_limit = 1.2    # seconds of silence before stop
        max_duration = 20      # hard limit safety
        chunk = 1024

        silence_counter = 0
        recording_started = False
        frames = []

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            device=MIC_DEVICE_INDEX
        ) as stream:

            start_time = time.time()

            while True:

                data, _ = stream.read(chunk)
                audio_chunk = data.flatten()
                volume = np.abs(audio_chunk).mean()

                if volume > threshold:
                    if not recording_started:
                        logger.info("Speech detected")
                        recording_started = True

                    silence_counter = 0
                    frames.append(audio_chunk)

                else:
                    if recording_started:
                        silence_counter += chunk / self.sample_rate
                        frames.append(audio_chunk)

                        if silence_counter > silence_limit:
                            logger.info("Silence detected. Stopping.")
                            break

                # safety limit
                if time.time() - start_time > max_duration:
                    logger.warning("Max duration reached. Stopping.")
                    break

        if not frames:
            return np.zeros(int(self.sample_rate * 0.5), dtype=np.int16)

        audio = np.concatenate(frames)
        return audio.astype(np.int16)

    # =========================================================
    # Transcription
    # =========================================================
    def transcribe(self) -> str:

        audio = self.record_audio()

        with NamedTemporaryFile(suffix=".wav", delete=False) as f:
            write(f.name, self.sample_rate, audio)

            with open(f.name, "rb") as audio_file:
                upload_res = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers={"authorization": ASSEMBLYAI_API_KEY},
                    data=audio_file
                )

                upload_url = upload_res.json()["upload_url"]

        transcript_res = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=self.headers,
            json={
                "audio_url": upload_url,
                "punctuate": True,
                "format_text": True
            }
        )

        transcript_id = transcript_res.json()["id"]

        start = time.time()
        timeout = 25

        while time.time() - start < timeout:

            poll = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=self.headers
            ).json()

            if poll["status"] == "completed":
                text = poll.get("text", "")
                logger.info(f"AssemblyAI → {text}")
                return text

            if poll["status"] == "error":
                raise RuntimeError(poll["error"])

            time.sleep(0.8)

        raise TimeoutError("AssemblyAI transcription timed out")
