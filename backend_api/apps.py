import os
import io
import time
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from transformers import BlipProcessor, BlipForConditionalGeneration
from gtts import gTTS
import torch

# ✅ Set Hugging Face cache directory to avoid space issues
os.environ["HF_HOME"] = "/home/ubuntu/hf_cache"

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ Allow CORS for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load BLIP Model and Processor with reduced RAM usage
try:
    print("🔄 Loading BLIP Processor and Model... (this may take a while)")
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        torch_dtype=torch.float16,  # Use less memory
        low_cpu_mem_usage=True      # Optimize for low CPU usage
    )
    print("✅ BLIP Model successfully loaded.")
except Exception as e:
    raise RuntimeError(f"❌ Error loading BLIP model: {e}")

# ✅ Audio file storage
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ✅ Logging setup
logging.basicConfig(level=logging.INFO, filename="app.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_caption(image):
    """Generate a caption for the given image using BLIP."""
    try:
        print("🔄 Generating caption...")
        inputs = blip_processor(image, return_tensors="pt")
        outputs = blip_model.generate(**inputs)
        caption = blip_processor.decode(outputs[0], skip_special_tokens=True)
        print(f"✅ Caption generated: {caption}")
        return caption
    except Exception as e:
        logger.error(f"❌ Caption generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate caption.")

def generate_audio(caption, filename):
    """Convert caption to an MP3 file using gTTS."""
    try:
        print(f"🔄 Generating audio for: {filename}")
        tts = gTTS(caption, lang="en")
        # Convert filename to lowercase
        filename_lower = filename.lower()
        audio_path = os.path.join(AUDIO_DIR, f"{filename_lower}.mp3")
        tts.save(audio_path)

        # ✅ Verify File Save
        if os.path.exists(audio_path):
            print(f"✅ Audio file saved: {audio_path}")
            return audio_path
        else:
            print(f"❌ Audio file not saved: {audio_path}")
            raise HTTPException(status_code=500, detail="Audio file was not saved.")

    except Exception as e:
        logger.error(f"❌ Audio generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio.")

async def delete_audio_file(audio_path: str):
    """Delete the audio file after 24 hours to save space."""
    try:
        await asyncio.sleep(24 * 60 * 60)  # Wait for 24 hours
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"🗑️ Deleted audio file: {audio_path}")
        else:
            logger.warning(f"⚠️ Tried to delete missing audio file: {audio_path}")
    except Exception as e:
        logger.error(f"❌ Error deleting audio file: {e}")

@app.post("/generate_caption")
async def process_image(image_file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Process an image to generate a caption and an audio description."""
    try:
        print(f"📂 Received file: {image_file.filename}")

        # ✅ Limit image size to prevent excessive memory usage (Max 10MB)
        if image_file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file is too large (max 10MB).")

        # ✅ Read image file
        image_data = await image_file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # ✅ Verify image format
        try:
            image.verify()
        except (UnidentifiedImageError, IOError):
            raise HTTPException(status_code=400, detail="Invalid image file.")

        # ✅ Generate caption and audio
        caption = generate_caption(image)
        audio_path = generate_audio(caption, image_file.filename)

        # ✅ Dynamic public audio URL
        server_url = os.getenv("PUBLIC_SERVER_URL", "http://13.48.29.42:8000")
        audio_url = f"{server_url}/get_audio/{image_file.filename.lower()}.mp3"

        # ✅ Schedule audio file deletion
        background_tasks.add_task(delete_audio_file, audio_path)

        return JSONResponse(content={"caption": caption, "audio_url": audio_url})

    except Exception as e:
        logger.error(f"❌ Error generating caption/audio: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/get_audio/{filename}")
async def get_audio(filename: str):
    """Serve the generated audio file."""
    # Convert filename to lowercase
    filename_lower = filename.lower()
    audio_path = os.path.join(AUDIO_DIR, filename_lower)
    if os.path.exists(audio_path):
        print(f"🎵 Serving audio file: {audio_path}")
        return StreamingResponse(open(audio_path, "rb"), media_type="audio/mp3")
    else:
        logger.warning(f"⚠️ Audio file not found: {filename_lower}")
        return JSONResponse(content={"error": "Audio file not found."}, status_code=404)

# ✅ Ensure Correct Port for Deployment
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Default to 8000 if not set
    print(f"🚀 Starting FastAPI Server at: http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
