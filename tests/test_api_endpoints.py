"""
Tests complets d'intégration des routes API FastAPI.
"""

import os
import io
import shutil
import tempfile
import unittest
from starlette.testclient import TestClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from backend.server import app


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_dir = tempfile.mkdtemp(prefix="api_test_")
        cls.sample_pdf = os.path.join(cls.test_dir, "sample.pdf")

        # Création d'un PDF d'essai de 4 pages
        c = canvas.Canvas(cls.sample_pdf, pagesize=letter)
        for i in range(1, 5):
            c.drawString(100, 700, f"Page {i}")
            c.showPage()
        c.save()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_frontend_index_serving(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("PDF Split Studio", resp.text)

    def test_pdf_info(self):
        resp = self.client.post("/api/pdf-info", json={"file_path": self.sample_pdf})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["info"]["page_count"], 4)

    def test_thumbnail_and_batch(self):
        # Thumbnail individuel
        resp = self.client.post("/api/thumbnail", json={
            "file_path": self.sample_pdf,
            "page_index": 0,
            "scale": 0.2
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data_url"].startswith("data:image/jpeg;base64,"))

        # Batch thumbnails
        resp_batch = self.client.post("/api/thumbnails-batch", json={
            "file_path": self.sample_pdf,
            "scale": 0.2
        })
        self.assertEqual(resp_batch.status_code, 200)
        thumbs = resp_batch.json()["thumbnails"]
        self.assertEqual(len(thumbs), 4)

    def test_split_endpoint(self):
        resp = self.client.post("/api/split", json={
            "file_path": self.sample_pdf,
            "mode": "page_by_page",
            "output_dir_mode": "custom",
            "custom_output_dir": self.test_dir,
            "create_subfolder": False,
            "quality_config": {"mode": "original"}
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["files_count"], 4)

    def test_merge_endpoint(self):
        resp = self.client.post("/api/merge", json={
            "files": [
                {"file_path": self.sample_pdf, "pages": "1-2", "rotation": 0},
                {"file_path": self.sample_pdf, "pages": "3-4", "rotation": 0}
            ],
            "output_dir_mode": "custom",
            "custom_output_dir": self.test_dir,
            "output_filename": "api_merged.pdf"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_pages"], 4)
        self.assertTrue(os.path.exists(data["output_path"]))


if __name__ == "__main__":
    unittest.main()
