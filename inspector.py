"""Inspect public HTML page metadata using the Python standard library."""
import argparse
import json
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts = []
        self.in_title = False
        self.description = None
        self.canonical_url = None
        self.og_title = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            identifier = (attributes.get("name") or attributes.get("property") or "").lower()
            value = attributes.get("content")
            if identifier == "description" and self.description is None:
                self.description = value
            elif identifier == "og:title" and self.og_title is None:
                self.og_title = value
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split() and self.canonical_url is None:
            self.canonical_url = attributes.get("href")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)


def inspect(url, timeout=10):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Provide a complete http:// or https:// URL")
    request = Request(url, headers={"User-Agent": "PageMetadataInspector/0.1 (+local CLI)"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            raise ValueError(f"Expected an HTML page; received {content_type or 'unknown content type'}")
        html = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        final_url = response.geturl()
    parser = MetadataParser()
    parser.feed(html)
    return {
        "url": final_url,
        "title": " ".join("".join(parser.title_parts).split()) or None,
        "description": parser.description,
        "canonical_url": urljoin(final_url, parser.canonical_url) if parser.canonical_url else None,
        "og_title": parser.og_title,
    }


def main():
    cli = argparse.ArgumentParser(description="Extract metadata from a public HTML webpage")
    cli.add_argument("url", help="Webpage URL, including https://")
    cli.add_argument("--timeout", type=float, default=10, help="Network timeout in seconds (default: 10)")
    args = cli.parse_args()
    if args.timeout <= 0:
        cli.error("--timeout must be greater than zero")
    try:
        print(json.dumps(inspect(args.url, timeout=args.timeout), indent=2, ensure_ascii=False))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
