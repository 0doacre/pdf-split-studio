"""
Serveur API FastAPI pour PDF Split & Merge Studio.
Exécuté 100% en local (127.0.0.1) hors-ligne.
Fournit les points de terminaison pour l'interface graphique et les dialogues Windows.
"""

import os
import sys
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.pdf_service import (
    get_pdf_info,
    split_pdf,
    merge_pdfs,
    format_size
)
from backend.thumbnail_service import (
    get_page_thumbnail_data_url,
    get_batch_thumbnails,
    clear_cache
)

# Dossier temporaire pour les téléversements par glisser-déposer
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_split_studio_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="PDF Split & Merge Studio Backend",
    description="Backend local 100% hors-ligne pour la manipulation avancée de PDF",
    version="1.0.0"
)

# Sécurité : Restreint à localhost uniquement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modèles de requêtes Pydantic
class PdfInfoRequest(BaseModel):
    file_path: str
    password: Optional[str] = None


class ThumbnailRequest(BaseModel):
    file_path: str
    page_index: int
    scale: float = 0.35
    password: Optional[str] = None


class BatchThumbnailsRequest(BaseModel):
    file_path: str
    page_indices: Optional[List[int]] = None
    scale: float = 0.35
    password: Optional[str] = None


class SplitRequest(BaseModel):
    file_path: str
    mode: str = "page_by_page"
    chunk_size: Optional[int] = 1
    num_parts: Optional[int] = 2
    range_string: Optional[str] = ""
    merge_ranges: Optional[bool] = False
    selected_pages: Optional[List[int]] = None
    selection_action: Optional[str] = "extract_separate"
    breakpoints: Optional[List[int]] = None
    output_dir_mode: str = "source"
    custom_output_dir: Optional[str] = None
    create_subfolder: bool = True
    naming_prefix: Optional[str] = None
    rotations: Optional[Dict[str, int]] = None
    metadata_config: Optional[Dict[str, Any]] = None
    quality_config: Optional[Dict[str, Any]] = None
    source_password: Optional[str] = None
    output_password: Optional[str] = None


class MergeFileItem(BaseModel):
    file_path: str
    pages: str = "all"
    rotation: int = 0
    password: Optional[str] = None


class MergeRequest(BaseModel):
    files: List[MergeFileItem]
    output_dir_mode: str = "first_file"
    custom_output_dir: Optional[str] = None
    output_filename: str = "Document_fusionne.pdf"
    metadata_config: Optional[Dict[str, Any]] = None
    quality_config: Optional[Dict[str, Any]] = None
    output_password: Optional[str] = None


class FolderRequest(BaseModel):
    folder_path: str


class ChooseFolderRequest(BaseModel):
    initial_dir: Optional[str] = None


@app.get("/api/health")
def api_health():
    """Vérification de l'état du serveur local."""
    return {"status": "ok", "mode": "offline", "version": "1.0.0"}


@app.post("/api/choose-file")
def api_choose_file():
    """
    Ouvre la boîte de dialogue native Windows pour choisir un PDF source.
    Retourne le chemin absolu et les métadonnées immédiates.
    """
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF",
            filetypes=[("Documents PDF", "*.pdf"), ("Tous les fichiers", "*.*")]
        )
        root.destroy()

        if not file_path:
            return {"selected": False, "file_path": None}

        # Normaliser le chemin Windows
        file_path = os.path.abspath(file_path)
        info = get_pdf_info(file_path)
        return {"selected": True, "file_path": file_path, "info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/choose-files")
def api_choose_files():
    """
    Ouvre la boîte de dialogue native Windows pour choisir plusieurs PDF (fusion).
    """
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_paths = filedialog.askopenfilenames(
            title="Sélectionner des fichiers PDF",
            filetypes=[("Documents PDF", "*.pdf"), ("Tous les fichiers", "*.*")]
        )
        root.destroy()

        if not file_paths:
            return {"selected": False, "files": []}

        results = []
        for fp in file_paths:
            norm_path = os.path.abspath(fp)
            try:
                info = get_pdf_info(norm_path)
                results.append({"file_path": norm_path, "info": info})
            except Exception:
                results.append({"file_path": norm_path, "error": "Impossible de lire le fichier"})

        return {"selected": True, "files": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/choose-folder")
def api_choose_folder(req: ChooseFolderRequest):
    """
    Ouvre la boîte de dialogue native Windows pour choisir un dossier de destination.
    """
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(
            title="Choisir le dossier de sauvegarde",
            initialdir=req.initial_dir if req.initial_dir and os.path.isdir(req.initial_dir) else ""
        )
        root.destroy()

        if not folder:
            return {"selected": False, "folder_path": None}

        return {"selected": True, "folder_path": os.path.abspath(folder)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/open-folder")
def api_open_folder(req: FolderRequest):
    """
    Ouvre directement l'Explorateur Windows sur le dossier spécifié.
    """
    folder = req.folder_path
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="Le dossier n'existe pas.")

    try:
        os.startfile(os.path.abspath(folder))
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'ouverture d'explorateur : {e}")


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """
    Prend en charge le glisser-déposer de fichiers depuis le navigateur.
    Sauvegarde localement dans le dossier temporaire sécurisé et analyse le PDF.
    """
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        # Éviter collisions de noms
        counter = 1
        stem, ext = os.path.splitext(file.filename)
        while os.path.exists(file_path):
            file_path = os.path.join(UPLOAD_DIR, f"{stem}_{counter}{ext}")
            counter += 1

        with open(file_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)

        info = get_pdf_info(file_path)
        return {"success": True, "file_path": file_path, "info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pdf-info")
def api_pdf_info(req: PdfInfoRequest):
    """Retourne les informations détaillées d'un PDF."""
    try:
        info = get_pdf_info(req.file_path, password=req.password)
        return {"success": True, "info": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/thumbnail")
def api_thumbnail(req: ThumbnailRequest):
    """Génère la miniature d'une page individuelle."""
    try:
        data_url = get_page_thumbnail_data_url(
            file_path=req.file_path,
            page_index=req.page_index,
            scale=req.scale,
            password=req.password
        )
        return {"success": True, "page_index": req.page_index, "data_url": data_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/thumbnails-batch")
def api_thumbnails_batch(req: BatchThumbnailsRequest):
    """Génère les miniatures en lot pour un affichage rapide."""
    try:
        thumbs = get_batch_thumbnails(
            file_path=req.file_path,
            page_indices=req.page_indices,
            scale=req.scale,
            password=req.password
        )
        return {"success": True, "thumbnails": thumbs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/split")
def api_split(req: SplitRequest):
    """Exécute la découpe d'un PDF."""
    try:
        options = req.model_dump()
        result = split_pdf(options)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/merge")
def api_merge(req: MergeRequest):
    """Exécute la fusion de plusieurs PDF."""
    try:
        options = req.model_dump()
        result = merge_pdfs(options)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Montage des fichiers statiques du frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
