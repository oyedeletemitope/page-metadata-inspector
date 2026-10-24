# Page Metadata Inspector

Small Python CLI for inspecting metadata on publicly accessible HTML webpages.

## Requirements

- Python 3.10 or later
- Network connection for live URL checks

## Run

```bash
python3 inspector.py https://example.com
```

The JSON response contains `url`, `title`, `description`, `canonical_url`, and `og_title`. Missing fields are `null`.

To change the request timeout:

```bash
python3 inspector.py https://example.com --timeout 20
```

## Test

```bash
python3 -m unittest discover -s tests -v
```

The tests use mocked HTML responses and do not require network access.

## Limitations

The inspector reads the initial HTML response; it does not execute JavaScript. Dynamic-only metadata may be absent. It limits reads to 2 MB and follows Python's default HTTP redirect handling. Use only URLs you have permission to fetch. This is a local demonstration CLI; do not expose it as a public URL-fetching service without additional protections against internal-network access.
