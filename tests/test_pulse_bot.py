"""
Unit tests for pulse_bot.py
Run with:  pytest tests/ -v
"""

import importlib
import sys
import types
import unittest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers to import the module under test
# ---------------------------------------------------------------------------

def load_module():
    """Import (or reload) pulse_bot so tests always get a fresh copy."""
    if "pulse_bot" in sys.modules:
        return importlib.reload(sys.modules["pulse_bot"])
    return importlib.import_module("pulse_bot")


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

WEATHER_PAYLOAD = {
    "current_condition": [
        {
            "temp_C": "22",
            "temp_F": "72",
            "FeelsLikeC": "21",
            "FeelsLikeF": "70",
            "humidity": "55",
            "weatherDesc": [{"value": "Partly cloudy"}],
            "windspeedKmph": "15",
            "winddir16Point": "NW",
            "visibility": "10",
            "uvIndex": "4",
        }
    ],
    "nearest_area": [
        {
            "areaName": [{"value": "London"}],
            "country": [{"value": "United Kingdom"}],
        }
    ],
}

QUOTE_PAYLOAD = [{"q": "The only way to do great work is to love what you do.", "a": "Steve Jobs"}]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFetchJson(unittest.TestCase):
    """fetch_json() — network layer."""

    def setUp(self):
        self.pb = load_module()

    def test_returns_parsed_json_on_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"key": "value"}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.pb.fetch_json("https://example.com", "test")

        self.assertEqual(result, {"key": "value"})

    def test_returns_none_on_http_error(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url=None, code=500, msg="Server Error", hdrs=None, fp=None
        )):
            result = self.pb.fetch_json("https://example.com", "test")

        self.assertIsNone(result)

    def test_returns_none_on_url_error(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable")):
            result = self.pb.fetch_json("https://example.com", "test")

        self.assertIsNone(result)


class TestGetWeather(unittest.TestCase):
    """get_weather() — parsing and error handling."""

    def setUp(self):
        self.pb = load_module()

    def test_parses_valid_payload(self):
        with patch.object(self.pb, "fetch_json", return_value=WEATHER_PAYLOAD):
            w = self.pb.get_weather("London")

        self.assertEqual(w["temp_c"], "22")
        self.assertEqual(w["description"], "Partly cloudy")
        self.assertIn("London", w["city"])

    def test_returns_error_key_when_fetch_fails(self):
        with patch.object(self.pb, "fetch_json", return_value=None):
            w = self.pb.get_weather("Nowhere")

        self.assertIn("error", w)

    def test_returns_error_key_on_bad_shape(self):
        with patch.object(self.pb, "fetch_json", return_value={"unexpected": True}):
            w = self.pb.get_weather("Somewhere")

        self.assertIn("error", w)


class TestGetQuote(unittest.TestCase):
    """get_quote() — parsing and fallback."""

    def setUp(self):
        self.pb = load_module()

    def test_parses_valid_payload(self):
        with patch.object(self.pb, "fetch_json", return_value=QUOTE_PAYLOAD):
            q = self.pb.get_quote()

        self.assertIn("great work", q["quote"])
        self.assertEqual(q["author"], "Steve Jobs")

    def test_falls_back_when_fetch_fails(self):
        with patch.object(self.pb, "fetch_json", return_value=None):
            q = self.pb.get_quote()

        self.assertIn("quote", q)
        self.assertIn("author", q)
        self.assertTrue(len(q["quote"]) > 0)


class TestBuildSummary(unittest.TestCase):
    """build_summary() — output shape."""

    def setUp(self):
        self.pb = load_module()

    def _mock_data(self):
        with patch.object(self.pb, "fetch_json", side_effect=[WEATHER_PAYLOAD, QUOTE_PAYLOAD]):
            return self.pb.build_summary("London")

    def test_contains_section_headers(self):
        summary = self._mock_data()
        self.assertIn("PULSE BOT", summary)
        self.assertIn("WEATHER", summary)
        self.assertIn("MOTIVATION", summary)

    def test_contains_temperature(self):
        summary = self._mock_data()
        self.assertIn("22", summary)   # temp_c from fixture

    def test_contains_quote_author(self):
        summary = self._mock_data()
        self.assertIn("Steve Jobs", summary)

    def test_summary_is_non_empty_string(self):
        summary = self._mock_data()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 100)


class TestMainWritesFile(unittest.TestCase):
    """main() — integration: file is written."""

    def setUp(self):
        self.pb = load_module()

    def test_writes_summary_file(self):
        import tempfile, os

        with patch.object(self.pb, "fetch_json", side_effect=[WEATHER_PAYLOAD, QUOTE_PAYLOAD]):
            with patch.object(self.pb, "OUTPUT_FILE", "test_summary_output.txt"):
                with patch("sys.argv", ["pulse_bot.py", "London"]):
                    self.pb.main()

        self.assertTrue(os.path.exists("test_summary_output.txt"))
        with open("test_summary_output.txt", encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("PULSE BOT", content)

        # Cleanup
        os.remove("test_summary_output.txt")


if __name__ == "__main__":
    unittest.main()
