import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure the library is importable from src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from oneCInteraction import Connection
from oneCInteraction.connection import mask_connection_string, format_com_error
import pywintypes


class TestServerConnection(unittest.TestCase):
    def test_legacy_positional_file_connection(self):
        conn = Connection("C:\\test\\db", "user1", "pass1")
        self.assertEqual(conn.s_oneCDatabasePath, "C:\\test\\db")
        self.assertIsNone(conn.s_server)
        self.assertIsNone(conn.s_database_name)
        self.assertEqual(conn.s_username, "user1")
        self.assertEqual(conn.s_password, "pass1")
        self.assertEqual(conn.s_prog_id, "V83.COMConnector")
        self.assertEqual(conn.s_connection_string, "File='C:\\test\\db';Usr='user1';Pwd='pass1';")

    def test_create_file_factory(self):
        conn = Connection.create_file("C:\\test\\db", "user1", "pass1", s_progIdIn="V83C.COMConnector")
        self.assertEqual(conn.s_oneCDatabasePath, "C:\\test\\db")
        self.assertEqual(conn.s_prog_id, "V83C.COMConnector")
        self.assertEqual(conn.s_connection_string, "File='C:\\test\\db';Usr='user1';Pwd='pass1';")

    def test_server_connection_initialization(self):
        conn = Connection(
            s_usernameIn="admin",
            s_passwordIn="12345",
            s_serverIn="srv",
            s_databaseNameIn="sportmaydan",
            s_progIdIn="Custom.COM"
        )
        self.assertIsNone(conn.s_oneCDatabasePath)
        self.assertEqual(conn.s_server, "srv")
        self.assertEqual(conn.s_database_name, "sportmaydan")
        self.assertEqual(conn.s_username, "admin")
        self.assertEqual(conn.s_password, "12345")
        self.assertEqual(conn.s_prog_id, "Custom.COM")
        self.assertEqual(conn.s_connection_string, "Srvr='srv';Ref='sportmaydan';Usr='admin';Pwd='12345';")

    def test_create_server_factory(self):
        conn = Connection.create_server(
            s_serverIn="srv",
            s_databaseNameIn="sportmaydan",
            s_usernameIn="admin",
            s_passwordIn="12345"
        )
        self.assertEqual(conn.s_server, "srv")
        self.assertEqual(conn.s_database_name, "sportmaydan")
        self.assertEqual(conn.s_prog_id, "V83.COMConnector")
        self.assertEqual(conn.s_connection_string, "Srvr='srv';Ref='sportmaydan';Usr='admin';Pwd='12345';")

    def test_validation_missing_all_params(self):
        with self.assertRaises(ValueError) as ctx:
            Connection()
        self.assertIn("Either s_oneCDatabasePathIn", str(ctx.exception))

    def test_validation_partial_server_params(self):
        with self.assertRaises(ValueError) as ctx:
            Connection(s_serverIn="srv")
        self.assertIn("Both s_serverIn and s_databaseNameIn must be provided", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            Connection(s_databaseNameIn="sportmaydan")
        self.assertIn("Both s_serverIn and s_databaseNameIn must be provided", str(ctx.exception))

    def test_validation_conflicting_params(self):
        with self.assertRaises(ValueError) as ctx:
            Connection(
                s_oneCDatabasePathIn="C:\\test\\db",
                s_serverIn="srv",
                s_databaseNameIn="sportmaydan"
            )
        self.assertIn("Cannot specify both", str(ctx.exception))

    def test_mask_connection_string(self):
        self.assertEqual(
            mask_connection_string("File='C:\\db';Usr='admin';Pwd='secret';"),
            "File='C:\\db';Usr='admin';Pwd='***';"
        )
        self.assertEqual(
            mask_connection_string("Srvr='srv';Ref='db';Usr='adm';pwd='pass123';"),
            "Srvr='srv';Ref='db';Usr='adm';pwd='***';"
        )
        self.assertEqual(mask_connection_string(""), "")

    def test_format_com_error_invalid_class_string(self):
        err = pywintypes.com_error(-2147221005, 'Invalid class string', None, None)
        formatted = format_com_error(err, "V83.COMConnector")
        self.assertIn("не зареєстровано в системі Windows", formatted)
        self.assertIn("comcntr.dll", formatted)
        self.assertIn("regsvr32", formatted)

    def test_format_com_error_1c_exception_info(self):
        exc_info = (0, "V83.COMConnector.1", "Неправильне ім'я користувача або пароль", None, 0, -2147467259)
        err = pywintypes.com_error(-2147352567, "Exception occurred.", exc_info, None)
        formatted = format_com_error(err)
        self.assertIn("Неправильне ім'я користувача або пароль", formatted)

    @patch("win32com.client.Dispatch")
    @patch("pythoncom.CoInitialize")
    def test_initiate_connection_calls_connector_with_server_string(self, mock_coinit, mock_dispatch):
        mock_connector = MagicMock()
        mock_v8 = MagicMock()
        mock_connector.Connect.return_value = mock_v8
        mock_dispatch.return_value = mock_connector

        conn = Connection.create_server("srv", "sportmaydan", "admin", "secret")
        # Prevent _cache_price_types from running queries on mock
        conn._cache_price_types = MagicMock()

        conn.initiate_connection()

        mock_dispatch.assert_called_once_with("V83.COMConnector")
        mock_connector.Connect.assert_called_once_with("Srvr='srv';Ref='sportmaydan';Usr='admin';Pwd='secret';")
        self.assertEqual(conn.c_v8, mock_v8)
        self.assertEqual(conn.s_last_error, "")

    @patch("win32com.client.Dispatch")
    @patch("pythoncom.CoInitialize")
    def test_initiate_connection_dispatch_failure(self, mock_coinit, mock_dispatch):
        mock_dispatch.side_effect = pywintypes.com_error(-2147221005, 'Invalid class string', None, None)

        conn = Connection.create_server("srv", "sportmaydan", "admin", "secret")
        conn.initiate_connection()

        self.assertIsNone(conn.c_v8)
        self.assertIn("не зареєстровано в системі Windows", conn.s_last_error)

    @patch("win32com.client.Dispatch")
    @patch("pythoncom.CoInitialize")
    def test_initiate_connection_connect_failure(self, mock_coinit, mock_dispatch):
        mock_connector = MagicMock()
        exc_info = (0, "V83.COMConnector.1", "Помилка автентифікації користувача", None, 0, -2147467259)
        mock_connector.Connect.side_effect = pywintypes.com_error(-2147352567, "Exception occurred.", exc_info, None)
        mock_dispatch.return_value = mock_connector

        conn = Connection.create_server("srv", "sportmaydan", "admin", "secret")
        conn.initiate_connection()

        self.assertIsNone(conn.c_v8)
        self.assertIn("Помилка автентифікації користувача", conn.s_last_error)

    @patch("win32com.client.Dispatch")
    @patch("pythoncom.CoInitialize")
    def test_initiate_connection_cache_failure_does_not_abort_connection(self, mock_coinit, mock_dispatch):
        mock_connector = MagicMock()
        mock_v8 = MagicMock()
        mock_connector.Connect.return_value = mock_v8
        mock_dispatch.return_value = mock_connector

        conn = Connection.create_server("srv", "sportmaydan", "admin", "secret")
        conn._cache_price_types = MagicMock(side_effect=RuntimeError("Price type table missing"))

        conn.initiate_connection()

        # Connection should remain alive even if price caching failed
        self.assertEqual(conn.c_v8, mock_v8)
        self.assertEqual(conn.s_last_error, "")

    def test_get_logs_dir_with_env_var(self):
        from oneCInteraction.log import get_logs_dir
        with patch.dict(os.environ, {"ONEC_LOGS_DIR": "C:\\custom\\logs\\path"}):
            self.assertEqual(get_logs_dir(), os.path.abspath("C:\\custom\\logs\\path"))

    @patch("win32com.client.Dispatch")
    @patch("pythoncom.CoInitializeEx")
    @patch("pythoncom.CoInitialize")
    def test_initiate_connection_coinitialize_mode_already_set(self, mock_coinit, mock_coinit_ex, mock_dispatch):
        mock_coinit_ex.side_effect = RuntimeError("Cannot change thread mode after it is set.")
        mock_connector = MagicMock()
        mock_v8 = MagicMock()
        mock_connector.Connect.return_value = mock_v8
        mock_dispatch.return_value = mock_connector

        conn = Connection.create_server("srv", "sportmaydan", "admin", "secret")
        conn._cache_price_types = MagicMock()
        conn.initiate_connection()

        self.assertEqual(conn.c_v8, mock_v8)
        self.assertEqual(conn.s_last_error, "")


if __name__ == "__main__":
    unittest.main()
