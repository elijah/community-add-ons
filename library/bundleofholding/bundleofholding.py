#!/usr/bin/env python3
"""Bundle of Holding library add-on.

Implements the library add-on script contract for Bundle of Holding:
- sync: list owned bundles from the Bundle of Holding API
- download: download a bundle or locate it locally
- scan: not applicable for Bundle of Holding (no local files)

Credentials are passed via the `config` object in the request JSON.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any


def _api_request(url: str, api_key: str) -> dict[str, Any]:
    """Make an authenticated request to the Bundle of Holding API."""
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Grimoire (+https://github.com/hunter-read/grimoire)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _list_bundles(api_key: str) -> list[dict[str, Any]]:
    """Fetch the user's owned bundles from Bundle of Holding."""
    url = "https://www.bundleofholding.com/api/v1/owned"
    try:
        data = _api_request(url, api_key)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("Invalid API key — check your Bundle of Holding credentials") from e
        raise RuntimeError(f"Bundle of Holding API error: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Bundle of Holding: {e.reason}") from e

    if not isinstance(data, list):
        raise RuntimeError("Unexpected response from Bundle of Holding API")

    return data


def _download_bundle(api_key: str, bundle_id: str) -> dict[str, Any]:
    """Download a bundle's contents."""
    url = f"https://www.bundleofholding.com/api/v1/bundles/{bundle_id}/download"
    try:
        data = _api_request(url, api_key)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Bundle not found: {bundle_id}") from e
        raise RuntimeError(f"Bundle of Holding API error: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Bundle of Holding: {e.reason}") from e

    return data


def _scan_local(_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Bundle of Holding does not scan local directories."""
    return []


def main() -> None:
    """Entry point — reads the request from stdin, writes the response to stdout."""
    try:
        request_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(json.dumps({"error": f"Invalid request: {e}"}))
        sys.exit(1)

    action = request_data.get("action")
    config = request_data.get("config", {})
    api_key = config.get("api_key", "")

    if not api_key:
        print(json.dumps({"error": "Missing api_key in config"}))
        sys.exit(1)

    try:
        if action == "sync":
            bundles = _list_bundles(api_key)
            resources = []
            for bundle in bundles:
                resources.append({
                    "id": str(bundle.get("id", "")),
                    "title": bundle.get("name", ""),
                    "authors": [bundle.get("publisher", "")] if bundle.get("publisher") else [],
                    "publisher": bundle.get("publisher", ""),
                    "year": bundle.get("year", 0),
                    "genres": bundle.get("genres", []),
                    "isbn": "",
                    "version": str(bundle.get("version", "1.0")),
                    "license": bundle.get("license", "Commercial"),
                    "urls": [bundle.get("url", "")] if bundle.get("url") else [],
                    "source_url": bundle.get("url", ""),
                    "download_url": bundle.get("download_url", ""),
                    "local_path": None,
                    "metadata": {
                        "bundle_id": bundle.get("id"),
                        "bundle_type": bundle.get("type", ""),
                        "contents": bundle.get("contents", []),
                    },
                })
            print(json.dumps({"resources": resources}))

        elif action == "download":
            resource_id = request_data.get("resource_id", "")
            if not resource_id:
                print(json.dumps({"error": "Missing resource_id"}))
                sys.exit(1)
            result = _download_bundle(api_key, resource_id)
            print(json.dumps(result))

        elif action == "scan":
            resources = _scan_local(config)
            print(json.dumps({"resources": resources}))

        else:
            print(json.dumps({"error": f"Unknown action: {action}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
