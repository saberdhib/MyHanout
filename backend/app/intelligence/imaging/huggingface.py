"""Provider d'images réel : text-to-image via HuggingFace Inference API.

Renvoie une image PNG encodée en data URL. Sans clé → erreur explicite (la
fabrique retombe alors sur le mock).
"""

from __future__ import annotations

import base64

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.imaging.base import GeneratedImage, ImageProvider

log = get_logger(__name__)


class HuggingFaceImageProvider(ImageProvider):
    name = "huggingface"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_image_model
        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model}"

    async def generate(  # pragma: no cover - réseau
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        if not self.api_key:
            raise RuntimeError("HUGGINGFACE_API_KEY manquante. Utilisez IMAGE_PROVIDER=mock.")
        payload = {
            "inputs": prompt,
            "parameters": {"width": width, "height": height},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/png",
                },
                json=payload,
            )
            resp.raise_for_status()
            content = resp.content
        b64 = base64.b64encode(content).decode("ascii")
        log.info("imaging.hf.generated", model=self.model, bytes=len(content))
        return GeneratedImage(
            data_url=f"data:image/png;base64,{b64}",
            media_type="image/png",
            prompt=prompt,
            provider=self.name,
        )
