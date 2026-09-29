"""Back up docs/private-notes to the PRIVATE repo, on its own branch.

    python tools/save_notes.py

The folder is gitignored on main so it can never reach the public copy. This
copies it onto an orphan branch called `notes`, commits, and pushes that
branch to `origin` (the private repo) only. Safe to run any time.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(ROOT, "docs", "private-notes")
BRANCH = "notes"


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def main():
    if not os.path.isdir(NOTES):
        print("nothing to save: docs/private-notes does not exist")
        return 1
    origin = git("remote", "get-url", "origin").stdout.strip()
    if "HoursNSilence" not in origin:
        print("refusing: origin is not the private repo:", origin)
        return 1
    tmp = tempfile.mkdtemp(prefix="hns-notes-")
    try:
        exists = git("ls-remote", "--heads", "origin", BRANCH).stdout.strip() != ""
        if exists:
            git("fetch", "origin", BRANCH)
            git("worktree", "add", tmp, f"origin/{BRANCH}", "--detach")
            git("checkout", "-B", BRANCH, cwd=tmp)
        else:
            git("worktree", "add", "--detach", tmp)
            git("checkout", "--orphan", BRANCH, cwd=tmp)
            git("rm", "-rfq", ".", cwd=tmp, check=False)
        dest = os.path.join(tmp, "private-notes")
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(NOTES, dest)
        with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("Private notes for Hours N Silence. This branch is never pushed to the public repo.\n")
        git("add", "-A", cwd=tmp)
        status = git("status", "--porcelain", cwd=tmp).stdout.strip()
        if not status:
            print("notes unchanged; nothing to commit")
        else:
            git("-c", "user.name=Dayian326", "-c", "user.email=dayian.nadeem326@gmail.com",
                "commit", "-qm", "notes: update", cwd=tmp)
            git("push", "-q", "origin", f"{BRANCH}:{BRANCH}", cwd=tmp)
            print(f"notes saved to origin/{BRANCH} (private repo only)")
    finally:
        git("worktree", "remove", "--force", tmp, check=False)
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
