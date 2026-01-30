import os
from typing import List
import fal_client
from fal_client import SyncClient

os.environ["FAL_KEY"] = "2502d69c-9c06-492a-9ef4-f081219e24ad:d46abb10980cb7048ae878f08606cac4"

def _ensure_image_urls(image_input: List[str]) -> List[str]:
    """
    fal model inputs want public URLs (or data URIs). If you pass local file paths,
    upload them to fal storage and use the returned URLs.
    """
    client = SyncClient()  # uses FAL_KEY from env by default
    urls: List[str] = []

    for item in image_input:
        if item.startswith(("http://", "https://", "data:")):
            urls.append(item)
        else:
            # Treat as local path -> upload to fal CDN
            urls.append(client.upload_file(item))

    return urls

def generate_image(prompt: str, image_input: List[str]) -> str:
    image_urls = _ensure_image_urls(image_input)

    result = fal_client.subscribe(
        "fal-ai/nano-banana/edit",
        arguments={
            "prompt": "Generate only the following object without context: " + prompt,
            "image_urls": image_urls,
            # Optional knobs (see model schema):
            # "num_images": 1,
            # "output_format": "png",
            # "aspect_ratio": "auto",
        },
    )

    return result["images"][0]["url"]