import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from fastapi import FastAPI, HTTPException
from twilio.rest import Client
import os
from google.cloud import texttospeech
import openai
from pydantic import BaseModel

# Configuración de claves de API (usar variables de entorno en producción)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GOOGLE_CLOUD_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializar servicios
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
text_to_speech_client = texttospeech.TextToSpeechClient()
openai.api_key = OPENAI_API_KEY

app = FastAPI()

# Modelo de datos para la llamada
class CallRequest(BaseModel):
    phone_number: str
    message: str

# Función para generar audio desde texto
def generate_speech(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="es-ES", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = text_to_speech_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    audio_file = "voice.mp3"
    with open(audio_file, "wb") as out:
        out.write(response.audio_content)
    return audio_file

# Endpoint para realizar una llamada
@app.post("/call")
def make_call(request: CallRequest):
    try:
        audio_file = generate_speech(request.message)
        call = client.calls.create(
            twiml=f'<Response><Play>{audio_file}</Play></Response>',
            to=request.phone_number,
            from_=TWILIO_PHONE_NUMBER
        )
        return {"call_sid": call.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para responder a una conversación con IA
@app.post("/chat")
def chat_ai(input_text: str):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "Eres un asistente de llamadas en español."},
                      {"role": "user", "content": input_text}]
        )
        return {"response": response["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Iniciar el servidor FastAPI con `uvicorn filename:app --reload`
