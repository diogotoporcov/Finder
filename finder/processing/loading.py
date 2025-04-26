from io import BytesIO
from pathlib import Path
from typing import Optional, Callable, Dict

import numpy as np
import requests
from PIL import Image

from finder.utils.utils import list_files, image_extensions, FilePath


def load_image_from_url(url: str) -> Optional[Image.Image]:
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def load_features(
        images_dir: FilePath,
        cache_dir: FilePath,
        extract_func: Callable[[Image.Image], np.ndarray],
        *,
        save_cache: bool = True,
        load_cache: bool = True
) -> Dict[Path, np.ndarray]:
    images_dir = Path(images_dir)
    cache_dir = Path(cache_dir)

    image_files = list_files(images_dir, image_extensions)
    cached_files = {file.stem: file for file in (list_files(cache_dir, "npy") if cache_dir.exists() else [])}

    features: Dict[Path, np.ndarray] = {}

    for path in image_files:
        path = Path(path)

        if load_cache and path.name in cached_files:
            # Load from cache if available
            feats: np.ndarray = np.load(cached_files[path.name])
            features[path] = feats
            continue

        # Extract features if cache does not exist
        img = Image.open(path).convert("RGB")
        feats: np.ndarray = extract_func(img)
        features[path] = feats

        if save_cache:
            cache_dir.mkdir(parents=True, exist_ok=True)
            np.save(cache_dir/path.name, feats)

    return features
