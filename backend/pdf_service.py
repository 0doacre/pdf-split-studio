"""
Service principal de traitement des PDF : découpe, fusion, rotation,
sécurisation et gestion des métadonnées.
100% hors-ligne et respectueux de la confidentialité des données.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from pypdf import PdfReader, PdfWriter
from backend.compression import optimize_writer


def format_size(size_bytes: int) -> str:
    """Formate une taille en octets en chaîne lisible (Ko, Mo, Go)."""
    if size_bytes < 1024:
        return f"{size_bytes} o"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} Ko"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} Mo"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} Go"


def sanitize_filename(name: Optional[str], default: str = "document") -> str:
    """Supprime les caractères interdits dans les noms de fichiers Windows."""
    if not name or not str(name).strip():
        return default
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", str(name)).strip()
    return sanitized if sanitized else default


def get_pdf_info(file_path: str, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyse un fichier PDF et retourne ses caractéristiques complètes :
    nombre de pages, taille, métadonnées, état de chiffrement et dimensions des pages.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier '{file_path}' n'existe pas.")

    file_size = os.path.getsize(file_path)
    file_dir = os.path.dirname(os.path.abspath(file_path))
    file_name = os.path.basename(file_path)
    stem, ext = os.path.splitext(file_name)

    reader = PdfReader(file_path)
    is_encrypted = reader.is_encrypted
    is_locked = False

    if is_encrypted:
        if password:
            decrypt_res = reader.decrypt(password)
            if decrypt_res == 0:
                is_locked = True
        else:
            # Tenter déchiffrement avec mot de passe vide par défaut
            try:
                reader.decrypt("")
            except Exception:
                is_locked = True

    if is_locked:
        return {
            "file_path": file_path,
            "file_name": file_name,
            "file_dir": file_dir,
            "stem": stem,
            "file_size": file_size,
            "file_size_formatted": format_size(file_size),
            "is_encrypted": True,
            "is_locked": True,
            "page_count": 0,
            "metadata": {},
            "pages": []
        }

    page_count = len(reader.pages)

    # Extraction des métadonnées
    raw_meta = reader.metadata or {}
    metadata = {
        "title": str(raw_meta.get("/Title", "") or ""),
        "author": str(raw_meta.get("/Author", "") or ""),
        "subject": str(raw_meta.get("/Subject", "") or ""),
        "creator": str(raw_meta.get("/Creator", "") or ""),
        "producer": str(raw_meta.get("/Producer", "") or ""),
        "creation_date": str(raw_meta.get("/CreationDate", "") or ""),
        "mod_date": str(raw_meta.get("/ModDate", "") or "")
    }

    # Analyse des dimensions des pages
    pages_info = []
    for i, page in enumerate(reader.pages):
        try:
            mb = page.mediabox
            w_pt = float(abs(mb.width))
            h_pt = float(abs(mb.height))
            rotation = int(page.get("/Rotate", 0) or 0) % 360
            is_landscape = (w_pt > h_pt and rotation in (0, 180)) or (h_pt > w_pt and rotation in (90, 270))
            pages_info.append({
                "page_number": i + 1,
                "width_pt": round(w_pt, 1),
                "height_pt": round(h_pt, 1),
                "rotation": rotation,
                "orientation": "landscape" if is_landscape else "portrait"
            })
        except Exception:
            pages_info.append({
                "page_number": i + 1,
                "width_pt": 595.0,
                "height_pt": 842.0,
                "rotation": 0,
                "orientation": "portrait"
            })

    return {
        "file_path": file_path,
        "file_name": file_name,
        "file_dir": file_dir,
        "stem": stem,
        "file_size": file_size,
        "file_size_formatted": format_size(file_size),
        "is_encrypted": is_encrypted,
        "is_locked": False,
        "page_count": page_count,
        "metadata": metadata,
        "pages": pages_info
    }


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    """
    Convertit une chaîne de sélection de pages (ex: "1-3, 5, 8-10", "even", "odd", "all")
    en une liste d'indices 0-indexés valides et ordonnés.
    """
    if not range_str or not range_str.strip():
        return list(range(max_pages))

    s = range_str.strip().lower()
    if s in ("all", "tout", "*"):
        return list(range(max_pages))
    elif s in ("even", "paires", "paire"):
        return [i for i in range(max_pages) if (i + 1) % 2 == 0]
    elif s in ("odd", "impaires", "impaire"):
        return [i for i in range(max_pages) if (i + 1) % 2 != 0]

    pages_set = set()
    parts = s.split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2:
                start_s, end_s = bounds[0].strip(), bounds[1].strip()
                try:
                    start = int(start_s) if start_s else 1
                    end = int(end_s) if end_s else max_pages
                    start = max(1, min(start, max_pages))
                    end = max(1, min(end, max_pages))
                    if start <= end:
                        for p in range(start, end + 1):
                            pages_set.add(p - 1)
                    else:
                        for p in range(start, end - 1, -1):
                            pages_set.add(p - 1)
                except ValueError:
                    raise ValueError(f"Intervalle de page invalide : '{part}'")
            else:
                raise ValueError(f"Format de plage invalide : '{part}'")
        else:
            try:
                p = int(part)
                if 1 <= p <= max_pages:
                    pages_set.add(p - 1)
                else:
                    raise ValueError(f"Page {p} hors limites (le document a {max_pages} pages)")
            except ValueError as e:
                if "hors limites" in str(e):
                    raise
                raise ValueError(f"Numéro de page invalide : '{part}'")

    return sorted(list(pages_set))


def apply_page_settings(
    writer: PdfWriter,
    rotations: Optional[Dict[str, int]] = None,
    metadata_config: Optional[Dict[str, Any]] = None,
    quality_config: Optional[Dict[str, Any]] = None,
    password: Optional[str] = None
) -> None:
    """
    Applique la rotation des pages, le nettoyage des métadonnées,
    l'optimisation/compression et le chiffrement optionnel par mot de passe.
    """
    # 1. Rotations
    if rotations:
        for idx_str, angle in rotations.items():
            try:
                page_idx = int(idx_str)
                angle_deg = int(angle) % 360
                if 0 <= page_idx < len(writer.pages) and angle_deg != 0:
                    writer.pages[page_idx].rotate(angle_deg)
            except (ValueError, TypeError):
                continue

    # 2. Métadonnées / Confidentialité
    meta_cfg = metadata_config or {}
    strip_meta = meta_cfg.get("strip_metadata", False)

    if strip_meta:
        # Nettoyage complet pour préserver la vie privée
        writer.add_metadata({
            "/Producer": "PDF Split Studio (Offline)",
            "/Creator": "PDF Split Studio",
            "/Title": meta_cfg.get("title", ""),
            "/Author": "",
            "/Subject": ""
        })
    elif meta_cfg.get("title") or meta_cfg.get("author"):
        custom_meta = {}
        if meta_cfg.get("title"):
            custom_meta["/Title"] = str(meta_cfg["title"])
        if meta_cfg.get("author"):
            custom_meta["/Author"] = str(meta_cfg["author"])
        writer.add_metadata(custom_meta)

    # 3. Optimisation & Compression
    optimize_writer(writer, quality_config)

    # 4. Chiffrement par mot de passe
    if password and password.strip():
        writer.encrypt(user_password=password.strip(), algorithm="AES-256")


def resolve_output_directory(
    source_file_path: str,
    output_dir_mode: str = "source",
    custom_dir: Optional[str] = None,
    create_subfolder: bool = True,
    subfolder_suffix: str = "_decoupe"
) -> str:
    """
    Détermine et crée le dossier d'exportation selon le choix utilisateur :
    - dossier source du PDF (avec ou sans sous-dossier propre)
    - dossier personnalisé choisi par l'utilisateur
    """
    source_dir = os.path.dirname(os.path.abspath(source_file_path))
    stem, _ = os.path.splitext(os.path.basename(source_file_path))

    if output_dir_mode == "custom" and custom_dir and os.path.isdir(custom_dir):
        base_dir = os.path.abspath(custom_dir)
    else:
        base_dir = source_dir

    if create_subfolder:
        target_dir = os.path.join(base_dir, f"{stem}{subfolder_suffix}")
    else:
        target_dir = base_dir

    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def split_pdf(options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exécute le découpage d'un PDF selon les multiples modes demandés :
    1. page_by_page : chaque page dans un fichier séparé
    2. chunk_size : paquets réguliers de N pages
    3. num_parts : division en X parties égales
    4. custom_ranges : plages personnalisées (ex: "1-3", "4-6")
    5. custom_selection : pages sélectionnées interactivement (séparées, fusionnées, ou supprimées)
    6. breakpoints : coupures à des pages spécifiques
    """
    file_path = options.get("file_path", "")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    source_password = options.get("source_password")
    reader = PdfReader(file_path)
    if reader.is_encrypted:
        if source_password:
            reader.decrypt(source_password)
        else:
            try:
                reader.decrypt("")
            except Exception:
                raise PermissionError("Le fichier PDF est protégé par mot de passe.")

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise ValueError("Le document PDF ne contient aucune page.")

    source_stem = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = resolve_output_directory(
        source_file_path=file_path,
        output_dir_mode=options.get("output_dir_mode", "source"),
        custom_dir=options.get("custom_output_dir"),
        create_subfolder=options.get("create_subfolder", True),
        subfolder_suffix="_decoupe"
    )

    mode = options.get("mode", "page_by_page")
    raw_prefix = options.get("naming_prefix") or source_stem
    naming_prefix = sanitize_filename(raw_prefix, default=source_stem)
    rotations = options.get("rotations") or {}
    metadata_config = options.get("metadata_config") or {}
    quality_config = options.get("quality_config") or {"mode": "original"}
    output_password = options.get("output_password")

    created_files: List[Dict[str, Any]] = []

    # Construction des paquets de pages selon le mode
    # Chaque élément de split_tasks est un tuple: (nom_fichier, [indices_pages_0_based])
    split_tasks: List[Tuple[str, List[int]]] = []

    if mode == "page_by_page":
        # Une page par fichier
        for i in range(total_pages):
            filename = f"{naming_prefix}_page_{i + 1}.pdf"
            split_tasks.append((filename, [i]))

    elif mode == "chunk_size":
        # Paquets de N pages
        chunk_size = max(1, int(options.get("chunk_size", 1)))
        for i in range(0, total_pages, chunk_size):
            chunk_indices = list(range(i, min(i + chunk_size, total_pages)))
            start_p = chunk_indices[0] + 1
            end_p = chunk_indices[-1] + 1
            if start_p == end_p:
                filename = f"{naming_prefix}_page_{start_p}.pdf"
            else:
                filename = f"{naming_prefix}_pages_{start_p}-{end_p}.pdf"
            split_tasks.append((filename, chunk_indices))

    elif mode == "num_parts":
        # Découpe en N parties égales ou équilibrées
        num_parts = max(1, min(total_pages, int(options.get("num_parts", 2))))
        # Répartition équitable
        k, m = divmod(total_pages, num_parts)
        start_idx = 0
        for part_num in range(1, num_parts + 1):
            part_len = k + (1 if part_num <= m else 0)
            if part_len == 0:
                continue
            chunk_indices = list(range(start_idx, start_idx + part_len))
            start_p = chunk_indices[0] + 1
            end_p = chunk_indices[-1] + 1
            filename = f"{naming_prefix}_partie_{part_num}_pages_{start_p}-{end_p}.pdf"
            split_tasks.append((filename, chunk_indices))
            start_idx += part_len

    elif mode == "custom_ranges":
        # Liste de plages saisies (ex: "1-3, 5, 8-10")
        range_str = options.get("range_string", "")
        merge_each_range = options.get("merge_ranges", False)
        
        # Découper en plages individuelles
        parts = [p.strip() for p in range_str.split(",") if p.strip()]
        if not parts:
            raise ValueError("Aucune plage de pages spécifiée.")

        all_collected_indices: List[int] = []

        for p_idx, part in enumerate(parts):
            indices = parse_page_ranges(part, total_pages)
            if not indices:
                continue
            if merge_each_range:
                all_collected_indices.extend(indices)
            else:
                start_p = indices[0] + 1
                end_p = indices[-1] + 1
                safe_part = sanitize_filename(part.replace(" ", ""))
                filename = f"{naming_prefix}_plage_{safe_part}.pdf"
                split_tasks.append((filename, indices))

        if merge_each_range and all_collected_indices:
            # Dédoublonner en conservant l'ordre
            seen = set()
            dedup = [x for x in all_collected_indices if not (x in seen or seen.add(x))]
            filename = f"{naming_prefix}_selection_fusionnee.pdf"
            split_tasks.append((filename, dedup))

    elif mode == "custom_selection":
        # Sélection interactive par l'utilisateur
        selected_pages = options.get("selected_pages", [])
        if not selected_pages:
            raise ValueError("Aucune page n'a été sélectionnée.")

        action = options.get("selection_action", "extract_separate")
        # conversion en entiers 0-indexed
        sel_indices = sorted(list(set([int(p) for p in selected_pages if 0 <= int(p) < total_pages])))

        if action == "extract_separate":
            for idx in sel_indices:
                filename = f"{naming_prefix}_page_{idx + 1}.pdf"
                split_tasks.append((filename, [idx]))

        elif action == "extract_merged":
            filename = f"{naming_prefix}_pages_extraites.pdf"
            split_tasks.append((filename, sel_indices))

        elif action == "delete_selected":
            # Conserver toutes les pages sauf celles sélectionnées
            keep_indices = [i for i in range(total_pages) if i not in sel_indices]
            if not keep_indices:
                raise ValueError("Vous avez sélectionné toutes les pages pour suppression.")
            filename = f"{naming_prefix}_sans_pages_supprimees.pdf"
            split_tasks.append((filename, keep_indices))

    elif mode == "breakpoints":
        # Points de coupure (ex: couper après la page 3 et après la page 7)
        raw_points = options.get("breakpoints", [])
        # Normaliser en numéros de page 1-indexed
        points = sorted(list(set([int(p) for p in raw_points if 1 <= int(p) < total_pages])))
        
        boundaries = [0] + points + [total_pages]
        for b_idx in range(len(boundaries) - 1):
            start = boundaries[b_idx]
            end = boundaries[b_idx + 1]
            chunk_indices = list(range(start, end))
            start_p = start + 1
            end_p = end
            filename = f"{naming_prefix}_section_{b_idx + 1}_pages_{start_p}-{end_p}.pdf"
            split_tasks.append((filename, chunk_indices))

    else:
        raise ValueError(f"Mode de découpage inconnu : {mode}")

    # Exécution de chaque tâche et écriture des fichiers
    total_output_bytes = 0

    for filename, page_indices in split_tasks:
        if not page_indices:
            continue

        writer = PdfWriter()
        for idx in page_indices:
            writer.add_page(reader.pages[idx])

        # Associer les rotations correspondantes aux pages du writer
        sub_rotations = {}
        for new_pos, orig_idx in enumerate(page_indices):
            if str(orig_idx) in rotations:
                sub_rotations[str(new_pos)] = rotations[str(orig_idx)]

        # Application des réglages
        apply_page_settings(
            writer=writer,
            rotations=sub_rotations,
            metadata_config=metadata_config,
            quality_config=quality_config,
            password=output_password
        )

        out_path = os.path.join(output_dir, filename)
        
        # En cas de collision de nom, incrémenter
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(out_path):
            out_path = os.path.join(output_dir, f"{base_name}_{counter}{ext}")
            counter += 1

        with open(out_path, "wb") as f_out:
            writer.write(f_out)

        file_sz = os.path.getsize(out_path)
        total_output_bytes += file_sz
        created_files.append({
            "filename": os.path.basename(out_path),
            "file_path": out_path,
            "page_count": len(page_indices),
            "file_size": file_sz,
            "file_size_formatted": format_size(file_sz)
        })

    orig_size = os.path.getsize(file_path)

    return {
        "success": True,
        "mode": mode,
        "output_dir": output_dir,
        "files_count": len(created_files),
        "files": created_files,
        "total_pages_processed": total_pages,
        "original_size": orig_size,
        "original_size_formatted": format_size(orig_size),
        "total_output_size": total_output_bytes,
        "total_output_size_formatted": format_size(total_output_bytes)
    }


def merge_pdfs(options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fusionne plusieurs fichiers PDF en ajoutant les pages données les unes à la suite.
    Permet de réorganiser, sélectionner des pages précises pour chaque fichier,
    ajuster la rotation, choisir la qualité et sécuriser par mot de passe.
    """
    file_items = options.get("files", [])
    if not file_items or len(file_items) < 1:
        raise ValueError("Veuillez sélectionner au moins un fichier PDF à fusionner.")

    first_file_path = file_items[0].get("file_path", "")
    output_dir = resolve_output_directory(
        source_file_path=first_file_path,
        output_dir_mode=options.get("output_dir_mode", "first_file"),
        custom_dir=options.get("custom_output_dir"),
        create_subfolder=False
    )

    raw_filename = options.get("output_filename") or "Document_fusionne.pdf"
    output_filename = sanitize_filename(raw_filename, default="Document_fusionne.pdf")
    if not output_filename.lower().endswith(".pdf"):
        output_filename += ".pdf"

    writer = PdfWriter()
    total_pages_added = 0
    total_input_bytes = 0

    for item in file_items:
        f_path = item.get("file_path", "")
        if not os.path.isfile(f_path):
            raise FileNotFoundError(f"Fichier à fusionner introuvable : {f_path}")

        total_input_bytes += os.path.getsize(f_path)
        pwd = item.get("password")
        reader = PdfReader(f_path)
        if reader.is_encrypted:
            if pwd:
                reader.decrypt(pwd)
            else:
                try:
                    reader.decrypt("")
                except Exception:
                    raise PermissionError(f"Le fichier '{os.path.basename(f_path)}' est protégé par mot de passe.")

        doc_pages = len(reader.pages)
        pages_to_include_str = item.get("pages", "all")
        indices = parse_page_ranges(pages_to_include_str, doc_pages)

        file_rotation = int(item.get("rotation", 0)) % 360

        for idx in indices:
            page = reader.pages[idx]
            if file_rotation != 0:
                page.rotate(file_rotation)
            writer.add_page(page)
            total_pages_added += 1

    if total_pages_added == 0:
        raise ValueError("Aucune page n'a été sélectionnée pour la fusion.")

    # Réglages qualité, métadonnées et mot de passe
    apply_page_settings(
        writer=writer,
        rotations=None,
        metadata_config=options.get("metadata_config", {}),
        quality_config=options.get("quality_config", {"mode": "original"}),
        password=options.get("output_password")
    )

    out_path = os.path.join(output_dir, output_filename)
    counter = 1
    stem, ext = os.path.splitext(output_filename)
    while os.path.exists(out_path):
        out_path = os.path.join(output_dir, f"{stem}_{counter}{ext}")
        counter += 1

    with open(out_path, "wb") as f_out:
        writer.write(f_out)

    out_size = os.path.getsize(out_path)

    return {
        "success": True,
        "output_dir": output_dir,
        "output_file": os.path.basename(out_path),
        "output_path": out_path,
        "total_pages": total_pages_added,
        "input_files_count": len(file_items),
        "total_input_size": total_input_bytes,
        "total_input_size_formatted": format_size(total_input_bytes),
        "output_size": out_size,
        "output_size_formatted": format_size(out_size)
    }
