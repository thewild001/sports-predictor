"""Check local agent executables and verify configured MCP server visibility where supported."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess

CHECKS = {
    "claude": ("claude", ["mcp", "list"], "native_mcp_list"),
    "opencode": ("opencode", ["mcp", "list"], "native_mcp_list"),
    "cursor": ("cursor", ["--version"], "manual_mcp_check_required"),
    "codex": ("codex", ["mcp", "list"], "native_mcp_list"),
    "pi": ("pi", ["mcp", "list", "--json"], "native_mcp_list"),
    "hermes": ("hermes", ["--version"], "manual_mcp_check_required"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=["all", *CHECKS], default="all")
    parser.add_argument("--server", default="sports-predictor")
    args = parser.parse_args()
    selected = CHECKS if args.client == "all" else {args.client: CHECKS[args.client]}
    results = []
    for name, (executable, command_args, verification) in selected.items():
        path = shutil.which(executable)
        if not path:
            results.append({"client": name, "status": "not_installed"})
            continue
        try:
            completed = subprocess.run([path, *command_args], capture_output=True, text=True,
                                       timeout=20, check=False)
            output = (completed.stdout + completed.stderr)[-4000:]
            if completed.returncode != 0:
                status = "command_failed"
            elif verification == "native_mcp_list":
                status = "server_visible" if args.server in output else "server_not_visible"
            else:
                status = "manual_check_required"
            results.append({"client": name, "status": status, "verification": verification,
                            "returncode": completed.returncode, "output": output})
        except subprocess.TimeoutExpired:
            results.append({"client": name, "status": "timeout"})
    print(json.dumps(results, indent=2, ensure_ascii=False))
    accepted = {"server_visible", "manual_check_required", "not_installed"}
    return 0 if all(item["status"] in accepted for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
