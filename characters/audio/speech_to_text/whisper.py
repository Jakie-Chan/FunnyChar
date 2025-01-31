import io
import os
import subprocess
import time
import types

import speech_recognition as sr
from faster_whisper import WhisperModel
from pydub import AudioSegment

from characters.audio.speech_to_text.base import SpeechToText
from characters.logger import get_logger
from characters.utils import Singleton, timed
from openai import OpenAI
client = OpenAI(
    base_url=os.getenv('OPENAI_WHISPER_BASE_URL'),
    api_key=os.getenv('OPENAI_WHISPER_API_KEY', 'api_key')
)

logger = get_logger(__name__)

config = types.SimpleNamespace(
    **{
        "model": os.getenv("LOCAL_WHISPER_MODEL", "base"),
        "language": "en",
        "api_key": os.getenv("OPENAI_WHISPER_API_KEY"),
    }
)

# Whisper use a shorter version for language code. Provide a mapping to convert
# from the standard language code to the whisper language code.
WHISPER_LANGUAGE_CODE_MAPPING = {
    "en-US": "en",
    "es-ES": "es",
    "fr-FR": "fr",
    "de-DE": "de",
    "it-IT": "it",
    "pt-PT": "pt",
    "hi-IN": "hi",
    "pl-PL": "pl",
    "zh-CN": "zh",
    "ja-JP": "jp",
    "ko-KR": "ko",
}


class Whisper(Singleton, SpeechToText):
    def __init__(self, use="local"):
        super().__init__()
        if use == "local":
            try:
                subprocess.check_output(["nvidia-smi"])
                device = "cuda"
            except Exception:
                device = "cpu"
            logger.info(
                f"Loading [Local Whisper] model: [{config.model}]({device}) ...")
            self.model = WhisperModel(
                model_size_or_path=config.model,
                device="auto",
                download_root=None,
            )
        self.recognizer = sr.Recognizer()
        self.use = use

    @timed
    def transcribe(self, audio_bytes, platform, prompt="", language="en-US", suppress_tokens=[-1]):
        logger.info("Transcribing audio...")
        if platform == "web":
            audio = self._convert_webm_to_wav(audio_bytes, self.use == "local")
        elif platform == "twilio":
            audio = self._ulaw_to_wav(audio_bytes, self.use == "local")
        else:
            audio = self._convert_bytes_to_wav(
                audio_bytes, self.use == "local")
        if self.use == "local":
            return self._transcribe(audio, prompt, suppress_tokens=suppress_tokens)
        elif self.use == "api":
            return self._transcribe_api(audio, prompt)

    def _transcribe(self, audio, prompt="", language="en-US", suppress_tokens=[-1]):
        language = WHISPER_LANGUAGE_CODE_MAPPING.get(language, config.language)
        segs, _ = self.model.transcribe(
            audio,
            language=language,
            vad_filter=True,
            initial_prompt=prompt,
            suppress_tokens=suppress_tokens,
        )
        text = " ".join([seg.text for seg in segs])
        return text

    def _transcribe_api(self, audio, prompt=""):
        logger.info("Starting _transcribe_api")
        try:
            # 将 AudioData 转换为字节流
            logger.info("Converting AudioData to byte stream")
            audio_data = audio.get_wav_data()

            # 将字节流转换为 BytesIO 对象并确保文件名和扩展名
            audio_file = io.BytesIO(audio_data)
            audio_file.name = 'audio.wav'  # Ensure the file has a proper name and extension

            # 调用新的 OpenAI 音频转录 API
            logger.info("Calling OpenAI Audio transcriptions API")
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            # 打印 transcription 对象类型和内容
            logger.info("Transcription object type: %s", type(transcription))
            logger.info("Transcription object content: %s", transcription)

            # 假设 transcription 是一个对象，检查其属性
            if hasattr(transcription, 'text'):
                text = transcription.text
                logger.info("Transcription completed successfully: %s", text)
                return text
            else:
                logger.error(
                    "Transcription object does not have 'text' attribute")
                raise TypeError(
                    "Transcription object does not have 'text' attribute")
        except Exception as e:
            logger.error(f"Error in _transcribe_api: {e}")
            raise

    def _convert_webm_to_wav(self, webm_data, local=True):
        logger.info("Converting webm to wav")
        webm_audio = AudioSegment.from_file(io.BytesIO(webm_data))
        wav_data = io.BytesIO()
        webm_audio.export(wav_data, format="wav")
        if local:
            return wav_data
        with sr.AudioFile(wav_data) as source:
            audio = self.recognizer.record(source)
        return audio

    def _convert_bytes_to_wav(self, audio_bytes, local=True):
        logger.info("Converting bytes to wav")
        if local:
            audio = io.BytesIO(sr.AudioData(
                audio_bytes, 44100, 2).get_wav_data())
            return audio
        return sr.AudioData(audio_bytes, 44100, 2)

    def _ulaw_to_wav(self, audio_bytes, local=True):
        logger.info("Converting ulaw to wav")
        sound = AudioSegment(data=audio_bytes, sample_width=1,
                             frame_rate=8000, channels=1)

        audio = io.BytesIO()
        sound.export(audio, format="wav")
        if local:
            return audio

        return sr.AudioData(audio_bytes, 8000, 1)
