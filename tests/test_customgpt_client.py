import io
import json
import unittest
from unittest import mock

from orchestrator.clients.customgpt import CustomGPTClient, CustomGPTError


class DummyResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))
        self.status = status

    def read(self):
        return self._buffer.read()

    def __enter__(self):
        self._buffer.seek(0)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._buffer.close()
        return False


class DummyBytesResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self._buffer = io.BytesIO(payload)
        self.status = status

    def read(self):
        return self._buffer.read()

    def __enter__(self):
        self._buffer.seek(0)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._buffer.close()
        return False


class TestCustomGPTClient(unittest.TestCase):
    def setUp(self):
        self.client = CustomGPTClient("test-key")

    def test_build_messages_url(self):
        url = self.client._build_messages_url(42, "session-1", page=2, order="asc")
        self.assertIn("/projects/42/conversations/session-1/messages", url)
        self.assertTrue(url.endswith("page=2&order=asc"))

    def test_get_conversation_messages_invalid_order(self):
        with self.assertRaises(ValueError):
            self.client.get_conversation_messages(1, "abc", order="invalid")

    def test_get_conversation_messages_success(self):
        expected_payload = {"status": "success", "data": {"messages": []}}
        dummy = DummyResponse(expected_payload)

        with mock.patch("orchestrator.clients.customgpt.request.urlopen", return_value=dummy) as mocked:
            data = self.client.get_conversation_messages(99, "sess-7", page=3, order="desc")

        self.assertEqual(data, expected_payload)
        mocked.assert_called_once()
        request_obj = mocked.call_args[0][0]
        self.assertEqual(request_obj.method, "GET")
        header_names = {name.lower() for name in request_obj.headers}
        self.assertIn("authorization", header_names)
        self.assertIn("page=3&order=desc", request_obj.full_url)

    def test_get_conversation_messages_non_dict_response(self):
        raw = DummyBytesResponse(b"[]")

        with mock.patch("orchestrator.clients.customgpt.request.urlopen", return_value=raw):
            with self.assertRaises(CustomGPTError):
                self.client.get_conversation_messages(1, "abc")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
