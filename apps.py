from flask import Flask, request, jsonify, send_file
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from gtts import gTTS
import io
import os

# Initialize Flask app
app = Flask(__name__)

# Load BLIP Model and Processor
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Function to generate caption
def generate_caption(image):
    inputs = blip_processor(image, return_tensors="pt")
    outputs = blip_model.generate(**inputs)
    caption = blip_processor.decode(outputs[0], skip_special_tokens=True)
    return caption

# Function to generate audio
def generate_audio(caption):
    tts = gTTS(caption, lang="en")
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    audio_io.seek(0)
    return audio_io

# API Endpoint to process the image
@app.route('/generate_caption', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files['image']
    image = Image.open(image_file.stream).convert("RGB")

    # Generate caption
    caption = generate_caption(image)

    # Generate audio
    audio_io = generate_audio(caption)

    # Return JSON response with caption and audio file
    return jsonify({
        "caption": caption,
        "audio_url": "/get_audio"
    }), 200

# Endpoint to get the audio
@app.route('/get_audio', methods=['GET'])
def get_audio():
    audio_io = generate_audio("This is a sample audio.")  # Replace with actual audio if needed
    return send_file(audio_io, mimetype='audio/mp3')

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
