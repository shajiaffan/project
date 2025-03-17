import os
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from transformers import BlipProcessor, BlipForConditionalGeneration
from gtts import gTTS
import io
import time
import asyncio
import logging
import uvicorn

# ✅ Set Hugging Face cache directory to avoid space issues
os.environ["HF_HOME"] = "/home/ubuntu/hf_cache"

# ✅ Initialize FastAPI
app = FastAPI()

# ✅ Add CORS Middleware (Allow Public Access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load BLIP Model and Processor
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# ✅ Directory to save audio files
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ✅ Logging configuration
logging.basicConfig(level=logging.INFO, filename="app.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_caption(image):
    """Generate a caption for the given image."""
    inputs = blip_processor(image, return_tensors="pt")
    outputs = blip_model.generate(**inputs)
    caption = blip_processor.decode(outputs[0], skip_special_tokens=True)
    return caption

def generate_audio(caption, filename):
    """Convert caption to audio and save it."""
    tts = gTTS(caption, lang="en")
    audio_path = os.path.join(AUDIO_DIR, f"{filename}.mp3")
    tts.save(audio_path)
    return audio_path

async def delete_audio_file(audio_path: str):
    """Delete the audio file after 24 hours safely."""
    try:
        await asyncio.sleep(24 * 60 * 60)  # Wait for 24 hours
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Deleted audio file: {audio_path}")
    except asyncio.CancelledError:
        logger.warning(f"Task cancelled: Deleting {audio_path}")
    except Exception as e:
        logger.error(f"Error while deleting audio file: {e}")

@app.post("/generate_caption")
async def process_image(image_file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Process the image to generate a caption and audio description."""
    try:
        image_data = await image_file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Verify if the file is an image
        try:
            image.verify()
        except (UnidentifiedImageError, IOError):
            raise HTTPException(status_code=400, detail="Invalid image file.")

        caption = generate_caption(image)
        audio_path = generate_audio(caption, image_file.filename)
        
        # ✅ Use Public Server URL for Mobile Access
        audio_url = f"https://your-public-server.com/get_audio/{image_file.filename}.mp3"

        # ✅ Add a background task for deletion
        background_tasks.add_task(delete_audio_file, audio_path)

        return JSONResponse(content={"caption": caption, "audio_url": audio_url})

    except Exception as e:
        logger.error(f"Error generating caption/audio: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/get_audio/{filename}")
async def get_audio(filename: str):
    """Serve the generated audio file."""
    audio_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(audio_path):
        return StreamingResponse(open(audio_path, "rb"), media_type="audio/mp3")
    else:
        logger.warning(f"Audio file {filename} not found.")
        return JSONResponse(content={"error": "Audio file not found."}, status_code=404)

# ✅ Ensure Correct Port for Deployment
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Default to 8000 if PORT is not set
    uvicorn.run(app, host="0.0.0.0", port=port)
