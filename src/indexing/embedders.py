"""Real image and text embedders. Needs the optional "vector" extra and a one-time model download.

SigLIP maps photos and text into one space, so a text question can find matching photos.
Hugging Face access is required the first time the model is loaded.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "google/siglip-base-patch16-224"


def _normalise(features: Any) -> list[list[float]]:
    return (features / features.norm(dim=-1, keepdim=True)).tolist()


class SigLIPEmbedder:
    def __init__(self, model_id: str = DEFAULT_MODEL) -> None:
        import torch
        from transformers import AutoModel, AutoProcessor

        self._torch = torch
        self._processor = AutoProcessor.from_pretrained(model_id)
        self._model = AutoModel.from_pretrained(model_id).eval()

    def embed_images(self, paths: Sequence[Path]) -> list[list[float]]:
        from PIL import Image
        from pillow_heif import register_heif_opener

        register_heif_opener()
        images = []
        for path in paths:
            with Image.open(path) as img:
                images.append(img.convert("RGB"))
        inputs = self._processor(images=images, return_tensors="pt")
        with self._torch.no_grad():
            return _normalise(self._model.get_image_features(**inputs))

    def embed_text(self, texts: Sequence[str]) -> list[list[float]]:
        inputs = self._processor(text=list(texts), padding="max_length", return_tensors="pt")
        with self._torch.no_grad():
            return _normalise(self._model.get_text_features(**inputs))
