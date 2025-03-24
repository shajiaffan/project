import os
import io
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from transformers import BlipProcessor, BlipForConditionalGeneration
from gtts import gTTS
import torch
from concurrent.futures import ThreadPoolExecutor

# ✅ Hugging Face cache directory
os.environ["HF_HOME"] = "/home/ubuntu/hf_cache"

# ✅ FastAPI app setup
app = FastAPI()

# ✅ CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load BLIP model
try:
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        low_cpu_mem_usage=True
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    blip_model.to(device)
except Exception as e:
    raise RuntimeError(f"Error loading BLIP model: {e}")

# ✅ Directories
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ✅ Logging
logging.basicConfig(level=logging.INFO, filename="app.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Thread pool
executor = ThreadPoolExecutor(max_workers=2)

# ✅ Image preprocessing
MAX_IMAGE_SIZE = (512, 512)
def preprocess_image(image):
    image.thumbnail(MAX_IMAGE_SIZE)
    return image

# ✅ Caption generation
def generate_caption(image):
    try:
        image = preprocess_image(image)
        inputs = blip_processor(image, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = blip_model.generate(**inputs, max_length=20, min_length=5)
        caption = blip_processor.decode(outputs[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        logger.error(f"Caption generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate caption.")

# ✅ Audio generation
def generate_audio(caption, filename):
    try:
        tts = gTTS(caption, lang="en")
        audio_path = os.path.join(AUDIO_DIR, f"{filename}.mp3")
        tts.save(audio_path)
        return audio_path
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audio.")

# ✅ Delete old audio
async def delete_audio_file(audio_path: str):
    await asyncio.sleep(24 * 60 * 60)
    if os.path.exists(audio_path):
        os.remove(audio_path)
        logger.info(f"Deleted audio file: {audio_path}")

# ✅ Main API
@app.post("/generate_caption")
async def process_image(image_file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        if image_file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file is too large (max 10MB).")

        image_data = await image_file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        try:
            image.verify()
        except (UnidentifiedImageError, IOError):
            raise HTTPException(status_code=400, detail="Invalid image file.")

        caption = generate_caption(image)
        executor.submit(generate_audio, caption, image_file.filename)

        server_url = "http://13.61.227.55:8000"
        audio_url = f"{server_url}/get_audio/{image_file.filename}.mp3"

        background_tasks.add_task(delete_audio_file, os.path.join(AUDIO_DIR, f"{image_file.filename}.mp3"))

        return JSONResponse(content={"caption": caption, "audio_url": audio_url})

    except Exception as e:
        logger.error(f"Error generating caption/audio: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ✅ Audio serving route (updated)
@app.get("/get_audio/{filename}")
async def get_audio(filename: str):
    audio_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(audio_path):
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",  # ✅ Correct MIME type
            filename=filename
        )
    else:
        logger.warning(f"Audio file {filename} not found.")
        return JSONResponse(content={"error": "Audio file not found."}, status_code=404)

# ✅ Launch server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
