"""Publish main to the public showcase repo, with a safety check.

    python tools/push_public.py

Refuses if docs/private-notes (or any private state file) is tracked on
main, so the private folder can never reach the public copy. Otherwise
pushes main and tags to the `public` remote.
"""
import subprocess
import sys

PRIVATE_PREFIXES = ("docs/private-notes/", "dj/", "artwork_cache/", "scratch/")
PRIVATE_FILES = ("hoursnsilence_state.json", "hoursnsilence.log")


def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def main():
    tracked = git("ls-files").stdout.splitlines()
    bad = [f for f in tracked if f.startswith(PRIVATE_PREFIXES) or f in PRIVATE_FILES]
    if bad:
        print("refusing to publish: private files are tracked on main:")
        for f in bad:
            print("  ", f)
        return 1
    remotes = git("remote").stdout.split()
    if "public" not in remotes:
        print("no `public` remote configured")
        return 1
    git("push", "-q", "public", "main:main")
    git("push", "-q", "public", "--tags")
    print("published main and tags to", git("remote", "get-url", "public").stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
