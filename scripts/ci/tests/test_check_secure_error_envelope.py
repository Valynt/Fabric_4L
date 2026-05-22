from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ci import check_secure_error_envelope as gate


class CheckSecureErrorEnvelopeTests(unittest.TestCase):
    def test_detects_raw_str_exception_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            services = root / "services"
            services.mkdir(parents=True)
            bad_file = services / "route.py"
            bad_file.write_text("raise HTTPException(status_code=500, detail=str(e))\n", encoding="utf-8")

            old_repo_root = gate.REPO_ROOT
            old_scan_roots = gate.SCAN_ROOTS
            gate.REPO_ROOT = root
            gate.SCAN_ROOTS = (services,)
            try:
                findings = gate.scan()
            finally:
                gate.REPO_ROOT = old_repo_root
                gate.SCAN_ROOTS = old_scan_roots

            self.assertEqual(len(findings), 1)
            self.assertIn("detail=str(e)", findings[0][2])

    def test_allows_safe_error_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            services = root / "services"
            services.mkdir(parents=True)
            ok_file = services / "route.py"
            ok_file.write_text('return JSONResponse(status_code=500, content={"code":"INTERNAL_ERROR","message":"An unexpected error occurred.","request_id":"req_1"})\n', encoding="utf-8")

            old_repo_root = gate.REPO_ROOT
            old_scan_roots = gate.SCAN_ROOTS
            gate.REPO_ROOT = root
            gate.SCAN_ROOTS = (services,)
            try:
                findings = gate.scan()
            finally:
                gate.REPO_ROOT = old_repo_root
                gate.SCAN_ROOTS = old_scan_roots

            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
