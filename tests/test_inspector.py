import io
import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from inspector import inspect, main


class MockResponse:
    def __init__(self, html, content_type="text/html; charset=utf-8", final_url="https://example.com/products"):
        self.body = io.BytesIO(html.encode("utf-8") if isinstance(html, str) else html)
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.final_url = final_url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, length):
        return self.body.read(length)

    def geturl(self):
        return self.final_url


class InspectorTests(unittest.TestCase):
    @patch("inspector.urlopen")
    def test_extracts_metadata(self, mocked):
        mocked.return_value = MockResponse('''<html><head><title> Test  page </title>
          <meta name="description" content="A demo">
          <meta property="og:title" content="Social title">
          <link rel="canonical" href="/canonical"></head></html>''')
        self.assertEqual(inspect("https://example.com/products"), {
            "url": "https://example.com/products",
            "title": "Test page",
            "description": "A demo",
            "canonical_url": "https://example.com/canonical",
            "og_title": "Social title",
        })

    def test_rejects_invalid_url(self):
        for url in ("example.com", "ftp://example.com", "https:///missing-host"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                inspect(url)

    @patch("inspector.urlopen")
    def test_rejects_non_html(self, mocked):
        mocked.return_value = MockResponse("{}", "application/json")
        with self.assertRaisesRegex(ValueError, "Expected an HTML page"):
            inspect("https://example.com/data")

    @patch("inspector.urlopen")
    def test_missing_metadata_returns_null(self, mocked):
        mocked.return_value = MockResponse("<html><head></head><body>Nothing</body></html>")
        result = inspect("https://example.com/")
        self.assertTrue(all(result[field] is None for field in ("title", "description", "canonical_url", "og_title")))

    @patch("inspector.urlopen")
    def test_redirect_reports_final_url_and_resolves_canonical(self, mocked):
        mocked.return_value = MockResponse('<link rel="canonical" href="about">', final_url="https://example.com/final/")
        result = inspect("https://example.com/start")
        self.assertEqual(result["url"], "https://example.com/final/")
        self.assertEqual(result["canonical_url"], "https://example.com/final/about")

    @patch("inspector.urlopen")
    def test_entities_decode_in_metadata(self, mocked):
        mocked.return_value = MockResponse('<title>A &amp; B</title><meta name="description" content="Tom &amp; Jerry">')
        result = inspect("https://example.com")
        self.assertEqual(result["title"], "A & B")
        self.assertEqual(result["description"], "Tom & Jerry")

    @patch("inspector.urlopen")
    def test_network_timeout_propagates(self, mocked):
        mocked.side_effect = TimeoutError("timed out")
        with self.assertRaises(TimeoutError):
            inspect("https://example.com")

    @patch("inspector.urlopen")
    def test_http_error_propagates(self, mocked):
        mocked.side_effect = HTTPError("https://example.com", 403, "Forbidden", {}, None)
        with self.assertRaises(HTTPError):
            inspect("https://example.com")

    @patch("inspector.urlopen")
    def test_passes_timeout_to_request(self, mocked):
        mocked.return_value = MockResponse("<title>Hi</title>")
        inspect("https://example.com", timeout=20)
        self.assertEqual(mocked.call_args.kwargs["timeout"], 20)

    @patch("inspector.inspect", side_effect=URLError("offline"))
    def test_cli_exits_nonzero_on_network_error(self, _mocked):
        with patch("sys.argv", ["inspector.py", "https://example.com"]), patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(main(), 1)
            self.assertIn("offline", err.getvalue())

    def test_cli_rejects_nonpositive_timeout(self):
        with patch("sys.argv", ["inspector.py", "https://example.com", "--timeout", "0"]), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exc:
                main()
            self.assertEqual(exc.exception.code, 2)

    @patch("inspector.urlopen")
    def test_respects_two_megabyte_read_limit(self, mocked):
        mocked.return_value = MockResponse("<title>Hi</title>")
        inspect("https://example.com")
        self.assertEqual(mocked.return_value.body.tell(), len("<title>Hi</title>"))
        # Explicitly verify the read argument via a spy response.
        class SpyResponse(MockResponse):
            def read(self, length):
                self.read_size = length
                return super().read(length)
        spy = SpyResponse("<title>Hi</title>")
        mocked.return_value = spy
        inspect("https://example.com")
        self.assertEqual(spy.read_size, 2_000_000)


if __name__ == "__main__":
    unittest.main()
