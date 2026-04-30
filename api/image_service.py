import requests
import io
import os
import uuid
from PIL import Image as PILImage

# In a real app, you'd use an environment variable for this
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.getenv("VERCEL"):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def generate_image_ai(prompt: str, user_id: int):
    # Enhancing the prompt for extreme photorealism (Real-Life Look)
    # Using 512x512 for much faster generation while maintaining quality
    quality_boost = ", photorealistic, hyper-realistic, 8k, highly detailed"
    enhanced_prompt = prompt + quality_boost
    
    import urllib.parse
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    seed = uuid.uuid4().int
    # Using 512x512 is significantly faster than 1024x1024
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true&seed={seed}"
    
    return pollinations_url

def save_image_locally(url: str):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image_bytes = response.content
        
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_bytes)
            
        return f"/uploads/{filename}"
    except Exception as e:
        print(f"Error saving image: {e}")
        return None
