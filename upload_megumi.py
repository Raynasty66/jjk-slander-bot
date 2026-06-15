import requests
import io
from PIL import Image
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_STORAGE_SECRET_KEY"))

CHARACTER = "Fushiguro Megumi"

IMAGE1_URL = "https://preview.redd.it/megumis-potential-life-v0-n786aosx1tqg1.jpeg?width=1080&format=pjpg&auto=webp&s=0c41a8d36af843dd13128c577b14bbc991abb1b2"
IMAGE2_URL = "https://i.redd.it/vak804omkpqg1.gif"

def upload_image(image_bytes: bytes) -> str:
    # Let Supabase auto-generate the imageKey UUID
    result = supabase.table("ImagesLocation").insert({"character": CHARACTER}).execute()
    print(f"Inserted DB row: {result.data}")
    image_key = result.data[0]["imageKey"]
    path = f"images/{image_key}"
    supabase.storage.from_("slander-stuff").upload(path, image_bytes, {"content-type": "image/jpeg"})
    return image_key

# --- Image 1: JPEG ---
print("Downloading image 1 (JPEG)...")
resp1 = requests.get(IMAGE1_URL, headers={"User-Agent": "Mozilla/5.0"})
resp1.raise_for_status()
img1 = Image.open(io.BytesIO(resp1.content)).convert("RGB")
buf1 = io.BytesIO()
img1.save(buf1, format="JPEG")
key1 = upload_image(buf1.getvalue())
print(f"Image 1 uploaded as: {key1}")

# --- Image 2: GIF -> JPEG (first frame) ---
print("Downloading image 2 (GIF)...")
resp2 = requests.get(IMAGE2_URL, headers={"User-Agent": "Mozilla/5.0"})
resp2.raise_for_status()
img2 = Image.open(io.BytesIO(resp2.content))
img2.seek(0)  # first frame
buf2 = io.BytesIO()
img2.convert("RGB").save(buf2, format="JPEG")
key2 = upload_image(buf2.getvalue())
print(f"Image 2 (GIF first frame) uploaded as: {key2}")

print("Done!")
