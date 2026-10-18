"""
Module d'optimisation et de compression de PDF.
100% hors-ligne, sans dépendance externe lourde.
Prend en charge la conservation sans perte (lossless) et la compression avancée.
"""

import io
from typing import Dict, Any, Optional
from PIL import Image
from pypdf import PdfWriter


PRESETS = {
    "original": {
        "name": "Qualité originale (Sans perte)",
        "recompress_images": False,
        "max_dpi": None,
        "jpeg_quality": 100,
        "compress_streams": True,
        "deduplicate": True
    },
    "high": {
        "name": "Haute qualité (Légère réduction)",
        "recompress_images": True,
        "max_dpi": 200,
        "jpeg_quality": 85,
        "compress_streams": True,
        "deduplicate": True
    },
    "medium": {
        "name": "Qualité standard (Équilibré)",
        "recompress_images": True,
        "max_dpi": 150,
        "jpeg_quality": 75,
        "compress_streams": True,
        "deduplicate": True
    },
    "low": {
        "name": "Forte compression (Taille minimale)",
        "recompress_images": True,
        "max_dpi": 96,
        "jpeg_quality": 55,
        "compress_streams": True,
        "deduplicate": True
    },
    "custom": {
        "name": "Personnalisée",
        "recompress_images": True,
        "max_dpi": 150,
        "jpeg_quality": 75,
        "compress_streams": True,
        "deduplicate": True
    }
}


def sanitize_image_for_jpeg(img: Image.Image) -> Image.Image:
    """
    Convertit une image Pillow dans un mode compatible JPEG (RGB ou L)
    en gérant proprement les transparences (fond blanc).
    """
    if img.mode == "RGB":
        return img
    elif img.mode == "L":
        return img
    elif img.mode in ("RGBA", "LA"):
        # Fond blanc pour remplacer la transparence
        bg = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1]
        bg.paste(img.convert("RGB"), mask=alpha)
        return bg
    elif img.mode == "P":
        # Palette (GIF/PNG 8-bit)
        converted = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        alpha = converted.split()[-1]
        bg.paste(converted.convert("RGB"), mask=alpha)
        return bg
    elif img.mode == "CMYK":
        return img.convert("RGB")
    else:
        return img.convert("RGB")


def optimize_writer(writer: PdfWriter, quality_config: Optional[Dict[str, Any]] = None) -> None:
    """
    Applique la stratégie de compression/optimisation sur un PdfWriter pypdf.
    - Si mode == 'original', garantit aucune modification des flux graphiques et images (lossless).
    - Si compression demandée, redimensionne et recompresse les images avec Pillow.
    """
    if not quality_config:
        quality_config = {"mode": "original"}

    mode = quality_config.get("mode", "original").lower()
    preset = PRESETS.get(mode, PRESETS["original"]).copy()

    # Si personnalisé, écraser les paramètres avec les entrées utilisateur
    if mode == "custom":
        if "max_dpi" in quality_config and quality_config["max_dpi"]:
            try:
                preset["max_dpi"] = int(quality_config["max_dpi"])
            except (ValueError, TypeError):
                pass
        if "jpeg_quality" in quality_config and quality_config["jpeg_quality"]:
            try:
                preset["jpeg_quality"] = max(10, min(95, int(quality_config["jpeg_quality"])))
            except (ValueError, TypeError):
                pass
        if "recompress_images" in quality_config:
            preset["recompress_images"] = bool(quality_config["recompress_images"])

    # 1. Traitement des images si compression avec perte activée
    if preset["recompress_images"]:
        max_dpi = preset.get("max_dpi") or 150
        target_quality = preset.get("jpeg_quality") or 75

        for page_idx, page in enumerate(writer.pages):
            try:
                # Calculer la dimension physique de la page en pouces (1 pt = 1/72 pouce)
                media_box = page.mediabox
                page_width_in = float(abs(media_box.width)) / 72.0
                page_height_in = float(abs(media_box.height)) / 72.0

                # Dimensions maximales acceptables en pixels pour cette page
                max_w_px = int(page_width_in * max_dpi) if page_width_in > 0 else 2000
                max_h_px = int(page_height_in * max_dpi) if page_height_in > 0 else 2000
                max_w_px = max(max_w_px, 800)
                max_h_px = max(max_h_px, 800)

                for img_key in list(page.images.keys()):
                    try:
                        img_file = page.images[img_key]
                        pil_img = img_file.image
                        orig_w, orig_h = pil_img.size

                        # Vérifier si l'image doit être redimensionnée
                        need_resize = (orig_w > max_w_px or orig_h > max_h_px)
                        processed_img = pil_img

                        if need_resize:
                            # Calculer le ratio en conservant l'aspect
                            ratio = min(max_w_px / orig_w, max_h_px / orig_h)
                            new_w = max(1, int(orig_w * ratio))
                            new_h = max(1, int(orig_h * ratio))
                            processed_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                        # Nettoyer le format pour encodage JPEG optimal
                        processed_img = sanitize_image_for_jpeg(processed_img)

                        # Remplacement dans pypdf
                        img_file.replace(processed_img, quality=target_quality)
                    except Exception:
                        # Si une image particulière ne peut pas être remplacée, on la laisse intacte
                        continue
            except Exception:
                continue

    # 2. Compression des flux de contenu (texte, tracés vectoriels)
    if preset.get("compress_streams", True):
        for page in writer.pages:
            try:
                page.compress_content_streams()
            except Exception:
                pass

    # 3. Déduplication des objets identiques (polices répétées, logos)
    if preset.get("deduplicate", True):
        try:
            # pypdf 6+ compatible arguments
            try:
                writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
            except TypeError:
                writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        except Exception:
            pass
