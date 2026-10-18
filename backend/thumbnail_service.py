"""
Service de génération de miniatures et prévisualisations de pages PDF.
Utilise pypdfium2 pour un rendu haute performance et ultra-rapide.
Comprend une mise en cache mémoire pour une navigation fluide.
"""

import io
import base64
from typing import Optional, Dict, Tuple
from PIL import Image
import pypdfium2 as pdfium


# Cache en mémoire : {(file_path, mtime, page_idx, scale): base64_str}
_THUMBNAIL_CACHE: Dict[Tuple[str, float, int, float], str] = {}
_MAX_CACHE_SIZE = 300


def clear_cache():
    """Vide le cache des miniatures."""
    global _THUMBNAIL_CACHE
    _THUMBNAIL_CACHE.clear()


def render_page_image(
    file_path: str,
    page_index: int,
    scale: float = 0.35,
    password: Optional[str] = None
) -> Image.Image:
    """
    Rend une page PDF en image PIL à l'échelle demandée.
    """
    doc = pdfium.PdfDocument(file_path, password=password)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Page {page_index + 1} hors limites (total: {len(doc)})")
        page = doc[page_index]
        # Rendu pypdfium2 en bitmap puis image PIL
        pil_image = page.render(scale=scale).to_pil()
        return pil_image
    finally:
        doc.close()


def get_page_thumbnail_data_url(
    file_path: str,
    page_index: int,
    scale: float = 0.35,
    password: Optional[str] = None,
    quality: int = 80
) -> str:
    """
    Génère une miniature encodée en data URL (data:image/jpeg;base64,...).
    Utilise le cache mémoire si disponible.
    """
    import os
    try:
        mtime = os.path.getmtime(file_path)
    except OSError:
        mtime = 0.0

    cache_key = (file_path, mtime, page_index, scale)
    if cache_key in _THUMBNAIL_CACHE:
        return _THUMBNAIL_CACHE[cache_key]

    pil_img = render_page_image(file_path, page_index, scale=scale, password=password)
    
    # Conversion en RGB si nécessaire pour JPEG
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
    raw_bytes = buf.getvalue()

    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64_str}"

    # Gestion de la taille du cache
    if len(_THUMBNAIL_CACHE) >= _MAX_CACHE_SIZE:
        # Supprime le premier tiers des éléments les plus anciens
        keys = list(_THUMBNAIL_CACHE.keys())[:100]
        for k in keys:
            _THUMBNAIL_CACHE.pop(k, None)

    _THUMBNAIL_CACHE[cache_key] = data_url
    return data_url


def get_batch_thumbnails(
    file_path: str,
    page_indices: Optional[list[int]] = None,
    scale: float = 0.35,
    password: Optional[str] = None
) -> Dict[int, str]:
    """
    Rend en lot les miniatures pour les pages spécifiées (ou toutes les pages si None).
    Très efficace car ouvre le document une seule fois.
    """
    results: Dict[int, str] = {}
    doc = pdfium.PdfDocument(file_path, password=password)
    try:
        total = len(doc)
        indices = page_indices if page_indices is not None else list(range(total))
        for idx in indices:
            if 0 <= idx < total:
                page = doc[idx]
                pil_img = page.render(scale=scale).to_pil()
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=75, optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                results[idx] = f"data:image/jpeg;base64,{b64}"
    finally:
        doc.close()

    return results
