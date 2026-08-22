#!/usr/bin/env python3
"""KALKI CLI — Local Agent Protocol & Repository Connector.

Usage:
    python scripts/kalki_cli.py connect [PATH] [--url http://localhost:8000] [--token TOKEN]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _get_git_info(path: Path) -> dict[str, str]:
    """Inspect local git repository metadata."""
    info = {"remote": "", "branch": "main", "status": "clean"}
    try:
        # Check if git repo
        subprocess.run(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
                       check=True, capture_output=True, text=True)
    except Exception:
        return info

    try:
        r = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            info["remote"] = r.stdout.strip()
    except Exception:
        pass

    try:
        b = subprocess.run(["git", "-C", str(path), "branch", "--show-current"],
                           capture_output=True, text=True)
        if b.returncode == 0:
            info["branch"] = b.stdout.strip() or "main"
    except Exception:
        pass

    try:
        s = subprocess.run(["git", "-C", str(path), "status", "--porcelain"],
                           capture_output=True, text=True)
        if s.returncode == 0:
            info["status"] = "dirty" if s.stdout.strip() else "clean"
    except Exception:
        pass

    return info


def connect_repository(path_str: str, api_url: str, token: str | None = None) -> int:
    path = Path(path_str).resolve()
    if not path.is_dir():
        print(f"Error: Path '{path}' does not exist or is not a directory.")
        return 1

    name = path.name
    git_info = _get_git_info(path)

    print(f"Connecting local repository:")
    print(f"  Name:   {name}")
    print(f"  Path:   {path}")
    print(f"  Branch: {git_info['branch']}")
    print(f"  Remote: {git_info['remote'] or '(none)'}")
    print(f"  Status: {git_info['status']}")

    endpoint = f"{api_url.rstrip('/')}/api/integrations/local/connect"
    payload = json.dumps({
        "name": name,
        "path": str(path),
        "git_remote": git_info["remote"],
        "current_branch": git_info["branch"],
        "status": "connected"
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                print(f"\nSuccessfully paired with KALKI Workspace!")
                print(f"  Project ID: {data['project']['id']}")
                return 0
            else:
                print(f"\nFailed to connect: {data}")
                return 1
    except urllib.error.URLError as e:
        print(f"\nConnection to KALKI server failed: {e}")
        print(f"Ensure KALKI is running at {api_url}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="KALKI Local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    connect_parser = subparsers.add_parser("connect", help="Pair a local repository with KALKI Workspace")
    connect_parser.add_argument("path", nargs="?", default=".", help="Local repository path (default: current directory)")
    connect_parser.add_argument("--url", default="http://localhost:8000", help="KALKI API server URL")
    connect_parser.add_argument("--token", default=None, help="KALKI session token")

    args = parser.parse_args()
    if args.command == "connect":
        return connect_repository(args.path, args.url, args.token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
