# Enable inference mode for better performance
import torch
from flask import Flask, request, jsonify, send_file
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from gtts import gTTS
import os

app = Flask(__name__)

# Load BLIP Model and Processor (Move to CPU)
device = torch.device("cpu")
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

# Generate Caption
def generate_caption(image):
    with torch.no_grad():  # Reduce memory usage
        inputs = blip_processor(image, return_tensors="pt").to(device)
        outputs = blip_model.generate(**inputs)
        caption = blip_processor.decode(outputs[0], skip_special_tokens=True)
    return caption

# Generate Audio
def generate_audio(caption, output_path):
    tts = gTTS(caption, lang="en")
    tts.save(output_path)
    return output_path

@app.route("/caption", methods=["POST"])
def caption_image():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        image_file = request.files["image"]
        image = Image.open(image_file).convert("RGB")

        # Generate caption
        caption = generate_caption(image)

        # Generate audio
        audio_path = "output.mp3"
        generate_audio(caption, audio_path)

        if not os.path.exists(audio_path):
            return jsonify({"error": "Audio file was not generated"}), 500

        return send_file(audio_path, mimetype="audio/mpeg", as_attachment=True, download_name="caption_audio.mp3")

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
