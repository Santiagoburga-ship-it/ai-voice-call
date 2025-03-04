import ssl
ssl._create_default_https_context = ssl._create_unverified_context
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env file

from fastapi import FastAPI, HTTPException
from twilio.rest import Client
import os
from google.cloud import texttospeech
from pydantic import BaseModel
from transformers import pipeline

# Load environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GOOGLE_CLOUD_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Ensure required environment variables are set
if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GOOGLE_CLOUD_CREDENTIALS]):
    raise ValueError("❌ ERROR: Missing required environment variables. Check your .env file!")

# Initialize API clients
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
text_to_speech_client = texttospeech.TextToSpeechClient()

# Initialize Mistral AI model from Hugging Face
chatbot = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.1")

app = FastAPI()

# Model for the call request
class CallRequest(BaseModel):
    phone_number: str
    message: str

# Function to generate speech (Local File - Needs Public Hosting)
def generate_speech(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="es-ES", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = text_to_speech_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    audio_file = "voice.mp3"
    with open(audio_file, "wb") as out:
        out.write(response.audio_content)

    return audio_file  # ❌ Twilio needs a public URL

# Endpoint to make a call using Twilio
@app.post("/call")
def make_call(request: CallRequest):
    try:
        call = client.calls.create(
            twiml=f'<Response><Say voice="alice" language="es-ES">{request.message}</Say></Response>',
            to=request.phone_number,
            from_=TWILIO_PHONE_NUMBER
        )
        return {"call_sid": call.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ **New Free AI Chat Endpoint using Mistral-7B**
@app.post("/chat")
def chat_ai(input_text: str):
    try:
        response = chatbot(f"Pregunta: {input_text}\nRespuesta:", max_length=200)
        return {"response": response[0]["generated_text"].strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Start FastAPI with `uvicorn main:app --reload`
