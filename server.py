import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Final, Dict, Optional, TypedDict

import aiofiles
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from finder.processing.features import FeaturesExtractor
from finder.processing.loading import load_features, load_image_from_url
from finder.processing.similarity import calc_similarities
from finder.utils.utils import bytes_to_hash, list_files, image_extensions, extract_name_extension


class RequestCacheEntry(TypedDict):
    created: datetime
    image: Image.Image
    hash: str
    features: np.ndarray
    saved: bool
    tweeted: bool
    tweet_id: Optional[int]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    asyncio.create_task(recurring_cleanup(60))
    asyncio.create_task(recurring_images_update(2 * 60))
    yield


load_dotenv()

# Global constants and variables
(IMAGES_DIR := Path(os.getenv("IMAGES_DIR_PATH"))).mkdir(exist_ok=True)
(CACHE_DIR := Path(os.getenv("CACHE_DIR_PATH"))).mkdir(exist_ok=True)
images: Dict[Path, np.ndarray] = {}
features_extractor = FeaturesExtractor()
requests_cache: Dict[str, RequestCacheEntry] = {}
request_expire: int = 3 * 60

# FastAPI app setup
app: Final[FastAPI] = FastAPI(lifespan=lifespan)


@app.get("/image/find")
async def find_image(request: Request, url: str, max_results: int = 5, max_similarity: Optional[float] = None):
    request_id = str(uuid.uuid1())

    if (file_name := extract_name_extension(url, str(request.base_url))) is not None:
        if not (IMAGES_DIR / file_name).exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Not Found",
                    "message": "The image could not be found in our database using the provided URL.",
                    "detail": "Please verify that the URL is correct and corresponds to an existing image in our database."
                }
            )

        image_url = f"{request.base_url}image/{file_name}"
        return JSONResponse(
            status_code=200,
            content={
                "request_id": request_id,
                "results": [
                    {
                        "url": image_url,
                        "similarity": 1.0
                    }
                ]
            }
        )

    try:
        image = load_image_from_url(url)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "message": f"Failed to load image from the provided URL: {str(e)}.",
            }
        )

    try:
        features = features_extractor.extract_features(image)

        results = calc_similarities(features, images, max_similarity=max_similarity)[:max_results]
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "message": f"An error occurred during similarity calculation: {str(e)}."
            }
        )

    image_hash = bytes_to_hash(image.tobytes()).hex()

    is_exact_match = bool(results) and results[0][1] >= 0.99

    requests_cache[request_id] = {
        "image": image,
        "hash": image_hash,
        "features": features,
        "created": datetime.now(),
        "saved": is_exact_match,
        "tweeted": is_exact_match,
        "tweet_id": None
    }

    return JSONResponse(
        status_code=200,
        content={
            "request_id": request_id,
            "results": [
                {
                    "url": f"{request.base_url}image/{path.name}",
                    "similarity": float(similarity),
                }
                for path, similarity in results
            ]
        }
    )


class SaveRequest(BaseModel):
    request_id: str


@app.post("/image/save")
async def save_image(request: Request, save_request: SaveRequest):
    request_id = save_request.request_id
    cache = requests_cache.get(request_id, None)

    if cache is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Not Found",
                "message": f"The request with ID {request_id} has either expired or could not be found.",
                "request_id": request_id
            }
        )

    save_path = (IMAGES_DIR / cache["hash"]).with_suffix(".jpeg")
    features_save_path = (CACHE_DIR / cache["hash"]).with_suffix(".jpeg.npy")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    features_save_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{request.base_url}image/{save_path.name}"

    if save_path.exists() and features_save_path.exists():
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Image already exists.",
                "message": f"The image has already been stored at the specified URL: {url}",
                "url": url
            }
        )

    with BytesIO() as byte_io:
        cache["image"].save(byte_io, format="JPEG")
        img_bytes = byte_io.getvalue()

    async with aiofiles.open(save_path, "wb") as img_file:
        await img_file.write(img_bytes)

    np.save(features_save_path, cache["features"])

    images[save_path] = cache["features"]
    cache["saved"] = True

    if cache["saved"] and cache["tweeted"]:
        requests_cache.pop(request_id)

    return JSONResponse(
        status_code=200,
        content={
            "message": f"The image has been successfully saved and can be accessed at {url}",
            "url": url
        }
    )


# Middlewares
# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Static files configuration
app.mount("/image", StaticFiles(directory=IMAGES_DIR, html=True), name="image")


# Helper functions
def update_images():
    global images, features_extractor

    if len(images) == len(list_files(IMAGES_DIR, image_extensions)):
        print("No images update was required.")
        return

    print("Loading images...")
    images = load_features(IMAGES_DIR, CACHE_DIR, features_extractor.extract_features)
    print(f"{len(images)} image(s) loaded!")


def cleanup_expired_requests():
    global requests_cache

    now = datetime.now()
    expired_keys = [key for key, entry in requests_cache.items() if
                    (now - entry['created']).total_seconds() > request_expire]
    for key in expired_keys:
        requests_cache.pop(key)
    print(f"Cleaned up {len(expired_keys)} expired requests ({len(requests_cache)} remaining).")


async def recurring_cleanup(cooldown: float):
    while True:
        await asyncio.sleep(cooldown)
        cleanup_expired_requests()


async def recurring_images_update(cooldown: float):
    while True:
        update_images()
        await asyncio.sleep(cooldown)
