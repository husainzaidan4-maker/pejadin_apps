import asyncio
import unittest
from unittest.mock import MagicMock, patch

from starlette.requests import Request

import main


class PublicationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.st = {
            "id": 42,
            "status": "DIAJUKAN",
            "tahun": 2026,
            "tgl_berangkat": "2026-10-01",
            "tgl_kembali": "2026-10-02",
        }
        self.spd = {
            "id": 9,
            "st_id": 42,
            "urutan": 1,
            "pegawai_id": 10,
            "hari": 2,
            "malam": 1,
            "tarif_inap": 500,
            "tiket": 300,
            "lain": 20,
            "jumlah": 0,
        }
        self.pegawai = {
            "id": 10,
            "nama": "Nama Terbaru",
            "nip": "001234",
            "golongan": "III/c",
            "pangkat": "Penata",
            "tingkat_biaya": "C",
            "jabatan": "Analis",
            "eselon": "III.a",
            "aktif": 1,
        }

    def make_request(self, body):
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/st/42/terbitkan",
                "headers": [(b"content-type", b"application/json")],
                "query_string": b"",
                "server": ("testserver", 80),
                "client": ("testclient", 123),
                "scheme": "http",
                "http_version": "1.1",
            },
            receive,
        )

    def test_terbitkan_persists_recalculated_result_and_current_employee_snapshot(self):
        cursor_st = MagicMock()
        cursor_st.fetchone.return_value = self.st
        cursor_duplicate = MagicMock()
        cursor_duplicate.fetchone.return_value = None
        cursor_spd = MagicMock()
        cursor_spd.fetchall.return_value = [self.spd]
        cursor_pegawai = MagicMock()
        cursor_pegawai.fetchone.return_value = self.pegawai

        connection = MagicMock()

        def execute(sql, params=()):
            if "select * from st where id=" in sql:
                return cursor_st
            if "select 1 from st where nomor=" in sql:
                return cursor_duplicate
            if "select * from spd where st_id=" in sql:
                return cursor_spd
            if "select * from pegawai where id=" in sql:
                return cursor_pegawai
            return MagicMock()

        connection.execute.side_effect = execute
        pool = MagicMock()
        pool.connection.return_value.__enter__.return_value = connection
        result = {
            "tarif_harian": 120,
            "uang_harian": 240,
            "uang_inap": 500,
            "taksi": 0,
            "tarif_rep": 0,
            "rep": 0,
            "jumlah": 1060,
            "batas": 1000,
            "flag": 0,
        }

        with (
            patch.object(main, "q", side_effect=[self.st, [self.spd]]),
            patch.object(main, "pool", pool),
            patch.object(main, "hitung", return_value=result),
            patch.object(main, "log") as audit_log,
        ):
            response = asyncio.run(
                main.aksi(
                    42,
                    "terbitkan",
                    self.make_request(b'{"nomor":"ST/2026/42"}'),
                    {"id": 7, "role": "PPK", "nama": "PPK"},
                )
            )

        self.assertEqual(response, {"id": 42, "status": "TERBIT"})
        spd_update = next(
            call for call in connection.execute.call_args_list
            if call.args[0].startswith("update spd set")
        )
        update_sql, update_values = spd_update.args
        self.assertIn("status='TERBIT'", update_sql)
        self.assertIn("Nama Terbaru", update_values)
        self.assertIn("001234", update_values)
        self.assertIn(120, update_values)
        self.assertIn(1060, update_values)
        audit_log.assert_called_once_with(
            {"id": 7, "role": "PPK", "nama": "PPK"},
            "TERBITKAN",
            "st",
            42,
            "ST/2026/42",
        )


if __name__ == "__main__":
    unittest.main()
