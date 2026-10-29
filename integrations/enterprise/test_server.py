"""Focused checks for the Enterprise scaffold's authentication boundary."""

import os
import unittest
from unittest.mock import patch

import server


class AuthenticationTests(unittest.TestCase):
    def test_missing_keys_refuse_requests_and_startup(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(server, "API_KEYS", {}):
            self.assertFalse(server.validate_api_key(None))
            self.assertFalse(server.validate_api_key("Bearer anything"))
            with patch.object(server.socketserver, "TCPServer") as listener:
                self.assertEqual(server.serve(8788), 2)
                listener.assert_not_called()

    def test_malformed_keys_refuse_startup_without_echoing_secrets(self):
        for value in ("secret-without-name", "valid:key,broken", "name:", ":key", "a:one,a:two"):
            with self.subTest(value=value), patch.dict(os.environ, {"HEADRON_API_KEYS": value}):
                with self.assertRaises(ValueError) as caught:
                    server.load_api_keys()
                self.assertNotIn(value, str(caught.exception))
                with patch.object(server.socketserver, "TCPServer") as listener:
                    self.assertEqual(server.serve(8788), 2)
                    listener.assert_not_called()

    def test_valid_keys_require_matching_bearer(self):
        with patch.dict(os.environ, {"HEADRON_API_KEYS": "one:secret,two:other"}):
            with patch.object(server, "API_KEYS", server.load_api_keys()):
                self.assertTrue(server.validate_api_key("Bearer secret"))
                self.assertTrue(server.validate_api_key("Bearer other"))
                for header in (None, "Bearer ", "Bearer wrong", "Basic secret"):
                    self.assertFalse(server.validate_api_key(header))

    def test_default_binding_is_loopback(self):
        self.assertEqual(server.serve.__defaults__, ("127.0.0.1",))

    def test_private_routes_require_bearer_but_health_is_public(self):
        handler = server.EnterpriseHandler.__new__(server.EnterpriseHandler)
        handler.headers = {}
        handler.send_error_json = unittest.mock.Mock()
        handler.handle_health = unittest.mock.Mock()
        handler.handle_tools = unittest.mock.Mock()
        with patch.object(server, "API_KEYS", {"test": "secret"}):
            handler.path = "/tools"
            handler.do_GET()
            handler.send_error_json.assert_called_once_with(401, "Invalid or missing API key")
            handler.handle_tools.assert_not_called()
            handler.path = "/health"
            handler.do_GET()
            handler.handle_health.assert_called_once()
            handler.path = "/tools"
            handler.headers = {"Authorization": "Bearer secret"}
            handler.do_GET()
            handler.handle_tools.assert_called_once()


if __name__ == "__main__":
    unittest.main()
