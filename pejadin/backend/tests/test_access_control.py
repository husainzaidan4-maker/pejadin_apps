import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main


class SuratTugasAccessTests(unittest.TestCase):
    def setUp(self):
        self.surat_tugas = {
            "id": 42,
            "status": "TERBIT",
            "tgl_berangkat": "2026-10-01",
            "tgl_kembali": "2026-10-02",
        }
        self.spd_rows = [
            {"id": 1, "pegawai_id": 10, "jumlah": 100},
            {"id": 2, "pegawai_id": 20, "jumlah": 200},
        ]

    def test_pegawai_detail_contains_only_their_spd_and_total(self):
        with patch.object(main, "q", side_effect=[self.surat_tugas, self.spd_rows]):
            result = main.std(
                42, {"role": "PEGAWAI", "pegawai_id": 20}
            )

        self.assertEqual([row["id"] for row in result["spd"]], [2])
        self.assertEqual(result["total"], 200)

    def test_pegawai_cannot_open_another_employees_surat_tugas(self):
        with patch.object(main, "q", side_effect=[self.surat_tugas, self.spd_rows]):
            with self.assertRaises(HTTPException) as error:
                main.std(42, {"role": "PEGAWAI", "pegawai_id": 30})

        self.assertEqual(error.exception.status_code, 403)

    def test_non_pegawai_roles_keep_all_spd(self):
        with patch.object(main, "q", side_effect=[self.surat_tugas, self.spd_rows]):
            result = main.std(42, {"role": "PPK"})

        self.assertEqual([row["id"] for row in result["spd"]], [1, 2])
        self.assertEqual(result["total"], 300)


if __name__ == "__main__":
    unittest.main()
