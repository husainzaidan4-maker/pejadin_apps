import unittest
from unittest.mock import MagicMock, patch

import main


class AuditLoggingTests(unittest.TestCase):
    def test_writes_both_audit_rows_in_one_transaction(self):
        connection = MagicMock()
        pool = MagicMock()
        pool.connection.return_value.__enter__.return_value = connection
        user = {"id": 7, "username": "auditor"}

        with patch.object(main, "pool", pool), patch.object(main, "NOW", return_value="now"):
            main.log(user, "TERBITKAN", "st", 42, "ST/2026/42")

        connection.transaction.assert_called_once_with()
        self.assertEqual(connection.execute.call_count, 2)
        self.assertIn("insert into audit(", connection.execute.call_args_list[0].args[0])
        self.assertIn("insert into audit_log(", connection.execute.call_args_list[1].args[0])

    def test_audit_log_write_failure_is_not_suppressed(self):
        connection = MagicMock()
        connection.execute.side_effect = [None, RuntimeError("audit_log unavailable")]
        pool = MagicMock()
        pool.connection.return_value.__enter__.return_value = connection

        with patch.object(main, "pool", pool):
            with self.assertRaisesRegex(RuntimeError, "audit_log unavailable"):
                main.log({"id": 7, "username": "auditor"}, "CETAK", "st", 42, "spd")

        connection.transaction.assert_called_once_with()
        self.assertEqual(connection.execute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
