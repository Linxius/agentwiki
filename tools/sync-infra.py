"""Sync infra files from current branch to main. No-op if unchanged."""
import subprocess
import sys
from pathlib import Path

INFRA_PATHS = [
    "AGENTS.md", "config.json", "requirements.txt", "TODO.md", "README.md",
    "tools", "templates", "docs",
]

CUR = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    capture_output=True, text=True,
).stdout.strip()

if CUR == "main":
    print("已在 main 分支，无需同步")
    sys.exit(0)

result = subprocess.run(
    ["git", "diff", "--quiet", "main", "HEAD", "--"] + INFRA_PATHS,
)
if result.returncode == 0:
    print("infra 无变更，跳过")
    sys.exit(0)

subprocess.run(["git", "checkout", "main"], check=True)
subprocess.run(
    ["git", "checkout", CUR, "--"] + INFRA_PATHS, check=True,
)
subprocess.run(
    ["git", "commit", "-m", f"sync: infra from {CUR}"],
    check=True,
)
subprocess.run(["git", "checkout", CUR], check=True)
print(f"✅ infra 已同步到 main")
