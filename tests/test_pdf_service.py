"""
Tests unitaires et d'intégration pour le service PDF.
Vérifie tous les modes de découpe, la fusion, la qualité, la sécurité et les métadonnées.
"""

import os
import shutil
import tempfile
import unittest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader
from backend.pdf_service import (
    get_pdf_info,
    parse_page_ranges,
    split_pdf,
    merge_pdfs,
    format_size
)


class TestPdfService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="pdf_test_")
        self.sample_pdf = os.path.join(self.temp_dir, "document_sample.pdf")
        
        # Créer un PDF d'essai de 6 pages avec du contenu et des métadonnées
        c = canvas.Canvas(self.sample_pdf, pagesize=letter)
        c.setTitle("Document Test")
        c.setAuthor("Testeur Anonyme")
        for i in range(1, 7):
            c.drawString(100, 700, f"Page {i} de démonstration")
            c.circle(300, 400, 50 * (i % 3 + 1))
            c.showPage()
        c.save()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_pdf_info(self):
        info = get_pdf_info(self.sample_pdf)
        self.assertEqual(info["page_count"], 6)
        self.assertFalse(info["is_encrypted"])
        self.assertEqual(info["metadata"]["title"], "Document Test")
        self.assertEqual(len(info["pages"]), 6)

    def test_parse_page_ranges(self):
        self.assertEqual(parse_page_ranges("1-3, 5", 6), [0, 1, 2, 4])
        self.assertEqual(parse_page_ranges("all", 4), [0, 1, 2, 3])
        self.assertEqual(parse_page_ranges("even", 6), [1, 3, 5])
        self.assertEqual(parse_page_ranges("odd", 6), [0, 2, 4])

    def test_split_page_by_page(self):
        res = split_pdf({
            "file_path": self.sample_pdf,
            "mode": "page_by_page",
            "output_dir_mode": "source",
            "create_subfolder": True,
            "quality_config": {"mode": "original"}
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["files_count"], 6)
        for f in res["files"]:
            self.assertTrue(os.path.exists(f["file_path"]))
            r = PdfReader(f["file_path"])
            self.assertEqual(len(r.pages), 1)

    def test_split_chunk_size(self):
        res = split_pdf({
            "file_path": self.sample_pdf,
            "mode": "chunk_size",
            "chunk_size": 2,
            "output_dir_mode": "source",
            "create_subfolder": False,
            "quality_config": {"mode": "original"}
        })
        self.assertTrue(res["success"])
        # 6 pages par paquets de 2 = 3 fichiers
        self.assertEqual(res["files_count"], 3)
        for f in res["files"]:
            r = PdfReader(f["file_path"])
            self.assertEqual(len(r.pages), 2)

    def test_split_num_parts(self):
        res = split_pdf({
            "file_path": self.sample_pdf,
            "mode": "num_parts",
            "num_parts": 3,
            "output_dir_mode": "custom",
            "custom_output_dir": self.temp_dir,
            "create_subfolder": False
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["files_count"], 3)

    def test_split_custom_selection_merged(self):
        # Extraire pages 1, 3, 5 dans 1 seul PDF
        res = split_pdf({
            "file_path": self.sample_pdf,
            "mode": "custom_selection",
            "selected_pages": [0, 2, 4],
            "selection_action": "extract_merged",
            "output_dir_mode": "source",
            "create_subfolder": False
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["files_count"], 1)
        r = PdfReader(res["files"][0]["file_path"])
        self.assertEqual(len(r.pages), 3)

    def test_split_delete_pages(self):
        # Supprimer page 2 et 4 (indices 1 et 3) -> reste 4 pages
        res = split_pdf({
            "file_path": self.sample_pdf,
            "mode": "custom_selection",
            "selected_pages": [1, 3],
            "selection_action": "delete_selected",
            "output_dir_mode": "source",
            "create_subfolder": False
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["files_count"], 1)
        r = PdfReader(res["files"][0]["file_path"])
        self.assertEqual(len(r.pages), 4)

    def test_merge_pdfs(self):
        # Créer un 2ème PDF
        pdf2 = os.path.join(self.temp_dir, "doc2.pdf")
        c = canvas.Canvas(pdf2, pagesize=letter)
        c.drawString(100, 700, "Doc 2 page 1")
        c.showPage()
        c.drawString(100, 700, "Doc 2 page 2")
        c.showPage()
        c.save()

        res = merge_pdfs({
            "files": [
                {"file_path": self.sample_pdf, "pages": "1-2"},
                {"file_path": pdf2, "pages": "all"}
            ],
            "output_dir_mode": "custom",
            "custom_output_dir": self.temp_dir,
            "output_filename": "final_fusion.pdf"
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["total_pages"], 4) # 2 from doc1 + 2 from doc2
        r = PdfReader(res["output_path"])
        self.assertEqual(len(r.pages), 4)

    def test_strip_metadata_privacy(self):
        res = split_pdf({
            "file_path": self.sample_pdf,
            "mode": "chunk_size",
            "chunk_size": 6,
            "metadata_config": {"strip_metadata": True},
            "output_dir_mode": "source",
            "create_subfolder": False
        })
        out_f = res["files"][0]["file_path"]
        r = PdfReader(out_f)
        meta = r.metadata or {}
        self.assertEqual(meta.get("/Author", ""), "")


if __name__ == "__main__":
    unittest.main()
