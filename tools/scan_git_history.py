"""Scan all reachable Git blobs for high-confidence secret patterns.

This intentionally reports only blob/path metadata and secret type, never the
matched secret value. It is conservative enough for CI and is not a substitute
for provider-side secret revocation if a real credential was ever committed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict

MAX_BLOB_BYTES = 2_000_000

PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI-style API key": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "JWT": re.compile(rb"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "credential-bearing database URL": re.compile(
        rb"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis)://[^\s:/]+:[^\s@/]+@",
        re.IGNORECASE,
    ),
}

SENSITIVE_LITERAL = re.compile(
    rb"""(?ix)
    (?:
        zello_password
        |zello_auth_token
        |zello_refresh_token
        |auth_token
        |refresh_token
        |private_key
        |signing_key
        |openai_api_key
        |gemini_api_key
        |huggingface(?:_api)?_key
        |database_url
    )
    \s*[:=]\s*
    ["']([^"'\r\n]{8,})["']
    """
)

PLACEHOLDER_MARKERS = (
    b"example",
    b"dummy",
    b"test",
    b"sample",
    b"placeholder",
    b"your_",
    b"your-",
    b"secret",
    b"password",
    b"token",
    b"...",
)


def run(*args: str) -> bytes:
    return subprocess.check_output(args)


def is_placeholder(value: bytes) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def main() -> int:
    raw = run("git", "rev-list", "--objects", "--all").decode("utf-8", errors="replace")
    paths_by_sha: dict[str, set[str]] = defaultdict(set)

    for line in raw.splitlines():
        sha, _, path = line.partition(" ")
        if path:
            paths_by_sha[sha].add(path)

    findings: list[tuple[str, str, str]] = []

    for sha, paths in paths_by_sha.items():
        try:
            if run("git", "cat-file", "-t", sha).strip() != b"blob":
                continue
            size = int(run("git", "cat-file", "-s", sha).strip())
            if size > MAX_BLOB_BYTES:
                continue
            data = run("git", "cat-file", "blob", sha)
        except (subprocess.CalledProcessError, ValueError):
            continue

        labels = set()
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                labels.add(label)

        for match in SENSITIVE_LITERAL.finditer(data):
            if not is_placeholder(match.group(1)):
                labels.add("sensitive credential literal")

        if labels:
            display_path = sorted(paths)[0] if paths else "<unknown path>"
            for label in sorted(labels):
                findings.append((sha[:12], display_path, label))

    if findings:
        print("Potential secrets found in Git history. Values are intentionally not printed.")
        for sha, path, label in findings:
            print(f"- {label}: {path} (blob {sha})")
        print("Do not make the repository public until each finding is reviewed and any real secret is revoked.")
        return 1

    print("No high-confidence secret patterns found in reachable Git history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
