"""Provider d'images mock : affiche SVG déterministe, keyless, zéro réseau.

Produit une vraie affiche promo (rendue par le navigateur via une data URL) aux
couleurs de la marque. Suffisant pour la démo et les tests sans clé API.
"""

from __future__ import annotations

import base64

from app.intelligence.imaging.base import GeneratedImage, ImageProvider

# Palette de marque (cf. branding MyHanout).
_BRAND = "#12B76A"
_NIGHT = "#0F172A"
_ACCENT = "#F59E0B"
_SURFACE = "#F1F5F9"


def _wrap(text: str, width: int = 22, max_lines: int = 3) -> list[str]:
    """Découpe un texte en lignes pour l'affiche (sans dépendance externe)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current.strip())
            current = word
        else:
            current = f"{current} {word}".strip()
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current.strip())
    return lines[:max_lines] or [""]


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class MockImageProvider(ImageProvider):
    name = "mock"

    async def generate(
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        tagline_lines = _wrap(prompt, width=24, max_lines=3)
        tspans = "".join(
            f'<tspan x="512" dy="{0 if i == 0 else 64}">{_esc(line)}</tspan>'
            for i, line in enumerate(tagline_lines)
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 1024 1024">'
            f'<rect width="1024" height="1024" fill="{_NIGHT}"/>'
            f'<circle cx="512" cy="300" r="220" fill="{_BRAND}" opacity="0.18"/>'
            f'<rect x="0" y="0" width="1024" height="14" fill="{_BRAND}"/>'
            f'<text x="64" y="110" fill="{_SURFACE}" font-family="Manrope,Arial,sans-serif" '
            f'font-size="34" font-weight="700">MyHanout</text>'
            f'<text x="512" y="300" fill="{_ACCENT}" font-family="Manrope,Arial,sans-serif" '
            f'font-size="180" font-weight="800" text-anchor="middle">PROMO</text>'
            f'<text x="512" y="470" fill="{_SURFACE}" font-family="Manrope,Arial,sans-serif" '
            f'font-size="48" font-weight="700" text-anchor="middle">{tspans}</text>'
            f'<rect x="262" y="640" width="500" height="120" rx="24" fill="{_BRAND}"/>'
            f'<text x="512" y="718" fill="#FFFFFF" font-family="Manrope,Arial,sans-serif" '
            f'font-size="44" font-weight="800" text-anchor="middle">ANTI-GASPILLAGE</text>'
            f'<text x="512" y="920" fill="{_SURFACE}" opacity="0.7" '
            f'font-family="Manrope,Arial,sans-serif" font-size="28" text-anchor="middle">'
            f"Offre locale &amp; limitee - jusqu'a epuisement</text>"
            f"</svg>"
        )
        b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return GeneratedImage(
            data_url=f"data:image/svg+xml;base64,{b64}",
            media_type="image/svg+xml",
            prompt=prompt,
            provider=self.name,
        )
