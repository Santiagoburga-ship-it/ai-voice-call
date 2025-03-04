import ssl
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from twilio.rest import Client
from google.cloud import texttospeech
from google.cloud import storage  # Fixed Import
from openai import OpenAI  # Using Mistral-7B for Chat
from pydantic import BaseModel

# Load environment variables
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GOOGLE_CLOUD_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")  # New for hosting audio files
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Ensure required environment variables are set
if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GOOGLE_CLOUD_CREDENTIALS, GCS_BUCKET_NAME, MISTRAL_API_KEY]):
    raise ValueError("❌ ERROR: Missing required environment variables. Check your .env file!")

# Initialize API clients
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
text_to_speech_client = texttospeech.TextToSpeechClient()
storage_client = storage.Client()
app = FastAPI()

# Model for the call request
class CallRequest(BaseModel):
    phone_number: str
    message: str

# Function to generate speech and upload to Google Cloud Storage
def generate_speech(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="es-ES", name="es-ES-Neural2-D", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    
    response = text_to_speech_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    audio_filename = "voice.mp3"
    
    # Save file locally
    with open(audio_filename, "wb") as out:
        out.write(response.audio_content)
    
    # Upload to Google Cloud Storage
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(audio_filename)
    blob.upload_from_filename(audio_filename, content_type='audio/mp3')
    blob.make_public()
    
    return blob.public_url  # Return the public URL

# Endpoint to make a call using Twilio with realistic AI voice
@app.post("/call")
def make_call(request: CallRequest):
    try:
        audio_url = generate_speech(request.message)
        call = client.calls.create(
            twiml=f'<Response><Play>{audio_url}</Play></Response>',
            to=request.phone_number,
            from_=TWILIO_PHONE_NUMBER
        )
        return {"call_sid": call.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to interact with AI Chat (Mistral-7B)
@app.post("/chat")
def chat_ai(input_text: str):
    try:
        client = OpenAI(api_key=MISTRAL_API_KEY)  # Using Mistral-7B API
        response = client.chat.completions.create(
            model="mistral-7b",
            messages=[
                {"role": "system", "content": "Eres un asistente de llamadas en español."},
                {"role": "user", "content": input_text}
            ]
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Start FastAPI with `uvicorn main:app --reload`
