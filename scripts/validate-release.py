#!/usr/bin/env python3
"""
validate-release.py -- Pre-push release validation for CCteam-creator.

Run from repo root:
    python scripts/validate-release.py                # core checks (offline, fast)
    python scripts/validate-release.py --check-deps   # also verify npm/PyPI package reachability

Exits 0 if all checks pass, 1 on any error.
Prints warnings but does not fail on them.

Checks performed:
  1. Version sync across 3 files (.claude-plugin/plugin.json, cn/.claude-plugin/plugin.json,
     .claude-plugin/marketplace.json)
  2. SKILL.md frontmatter is valid YAML (not Markdown heading, has closing ---)
  3. Three-name alignment: plugin.json name == skill directory name == SKILL.md frontmatter name
     (for both EN and CN variants)
  4. EN/CN parallel file structure
  5. (--check-deps only) MCP packages referenced in mcp-setup.md actually exist
     on npm registry / PyPI — catches "phantom dependency" docs that 404 on user install.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

errors = []
warnings_list = []


def fail(msg):
    errors.append(msg)
    print(f"  [FAIL] {msg}")


def warn(msg):
    warnings_list.append(msg)
    print(f"  [WARN] {msg}")


def ok(msg):
    print(f"  [OK] {msg}")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Cannot read JSON at {path.relative_to(REPO_ROOT)}: {e}")
        return None


def parse_frontmatter(md_path):
    """Extract YAML frontmatter. Returns (dict, error_msg). dict is None on error."""
    if not md_path.exists():
        return None, f"File not found: {md_path}"
    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "Frontmatter does not start with '---' on line 1"
    # Find closing ---
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, "No closing '---' found -- frontmatter never terminates. Add '---' after the description block."
    body_lines = lines[1:end]
    body = "\n".join(body_lines)
    # Detect Markdown heading as field name (historical bug: "## name: setup")
    if re.search(r"^\s*#+\s+\w+\s*:", body, re.MULTILINE):
        return None, "Frontmatter contains a Markdown heading like '## name:'. Remove the '##' -- YAML keys have no prefix."
    # Minimal YAML parse: top-level key: value pairs, supports '>' block scalar
    result = {}
    current_key = None
    current_val_lines = []
    in_block_scalar = False
    key_re = re.compile(r"^(\w[\w-]*)\s*:\s*(.*)$")
    for line in body_lines:
        if in_block_scalar:
            if line.strip() == "" or line.startswith(" ") or line.startswith("\t"):
                if line.strip():
                    current_val_lines.append(line.strip())
                continue
            # New top-level key closes block scalar
            result[current_key] = " ".join(current_val_lines).strip()
            current_key = None
            current_val_lines = []
            in_block_scalar = False
        m = key_re.match(line)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip()
            if val in (">", "|"):
                in_block_scalar = True
                current_val_lines = []
            else:
                result[current_key] = val
                current_key = None
    if current_key:
        result[current_key] = " ".join(current_val_lines).strip()
    return result, None


def get_nested(d, key_path):
    """Get nested dict value by dot-separated path."""
    parts = key_path.split(".")
    v = d
    for p in parts:
        if not isinstance(v, dict):
            return None
        v = v.get(p)
    return v


def check_versions():
    """Verify all three version fields are in sync."""
    print("\n=== Check 1: Version sync ===")
    files = [
        (REPO_ROOT / ".claude-plugin" / "plugin.json", "version"),
        (REPO_ROOT / "cn" / ".claude-plugin" / "plugin.json", "version"),
        (REPO_ROOT / ".claude-plugin" / "marketplace.json", "metadata.version"),
    ]
    versions = {}
    for path, key in files:
        data = load_json(path)
        if data is None:
            continue
        v = get_nested(data, key)
        rel = path.relative_to(REPO_ROOT)
        if v is None:
            fail(f"{rel}: missing '{key}' field")
        else:
            versions[str(rel)] = v
            ok(f"{rel}: {v}")
    unique = set(versions.values())
    if len(unique) > 1:
        fail(f"Version mismatch across files: {versions}")
    elif len(unique) == 1:
        ok(f"All three versions in sync: {list(unique)[0]}")


def check_skill_variant(variant_label, plugin_json_path, skill_dir_path, expected_plugin_name):
    """Check one skill variant (EN or CN) for naming invariants."""
    print(f"\n=== Check: {variant_label} ===")
    pj = load_json(plugin_json_path)
    if pj is None:
        return
    actual_plugin_name = pj.get("name")
    if actual_plugin_name != expected_plugin_name:
        fail(f"{plugin_json_path.relative_to(REPO_ROOT)}: name is '{actual_plugin_name}', expected '{expected_plugin_name}'")
        return
    ok(f"plugin.json name: {actual_plugin_name}")
    if not skill_dir_path.exists():
        fail(f"Skill directory not found: {skill_dir_path.relative_to(REPO_ROOT)}")
        return
    ok(f"Skill directory exists: {skill_dir_path.relative_to(REPO_ROOT)}")
    dir_name = skill_dir_path.name
    if dir_name != expected_plugin_name:
        fail(
            f"Skill directory name is '{dir_name}', must be '{expected_plugin_name}' "
            f"(should match plugin name). Rename: git mv {skill_dir_path.relative_to(REPO_ROOT)} "
            f"{skill_dir_path.parent.relative_to(REPO_ROOT)}/{expected_plugin_name}"
        )
    else:
        ok(f"Skill directory name matches plugin name")
    skill_md = skill_dir_path / "SKILL.md"
    if not skill_md.exists():
        fail(f"SKILL.md not found at {skill_md.relative_to(REPO_ROOT)}")
        return
    frontmatter, err = parse_frontmatter(skill_md)
    if err:
        fail(f"SKILL.md frontmatter: {err}")
        return
    ok("SKILL.md frontmatter is parseable YAML")
    fm_name = frontmatter.get("name", "").strip()
    if fm_name != expected_plugin_name:
        fail(
            f"SKILL.md frontmatter 'name' is '{fm_name}', must be '{expected_plugin_name}' "
            f"(matches plugin name)"
        )
    else:
        ok(f"SKILL.md frontmatter name: {fm_name}")
    if not frontmatter.get("description"):
        warn("SKILL.md has no 'description' field")
    else:
        ok("SKILL.md has description field")


def check_parallel_structure():
    """Verify EN and CN have parallel file structure."""
    print("\n=== Check: EN/CN parallel structure ===")
    en_dir = REPO_ROOT / "skills" / "CCteam-creator"
    cn_dir = REPO_ROOT / "cn" / "skills" / "CCteam-creator-cn"
    if not (en_dir.exists() and cn_dir.exists()):
        return  # Missing dir already reported
    en_files = {str(f.relative_to(en_dir)) for f in en_dir.rglob("*") if f.is_file()}
    cn_files = {str(f.relative_to(cn_dir)) for f in cn_dir.rglob("*") if f.is_file()}
    en_only = sorted(en_files - cn_files)
    cn_only = sorted(cn_files - en_files)
    if en_only:
        warn(f"Files in EN but not CN: {en_only}")
    if cn_only:
        warn(f"Files in CN but not EN: {cn_only}")
    if not en_only and not cn_only:
        ok(f"EN and CN have identical file structure ({len(en_files)} files each)")


def check_external_deps():
    """(Optional, --check-deps) Verify MCP packages in mcp-setup.md exist on npm/PyPI.

    Catches the "phantom dependency" failure mode where docs reference packages
    that 404 on user install. Skipped by default since it requires network calls.
    Uses system `curl` (not urllib) to avoid macOS Python SSL cert issues.
    """
    if "--check-deps" not in sys.argv:
        return

    print("\n=== Check 5: External MCP dependency reachability ===")

    npm_packages = set()
    pypi_packages = set()

    mcp_setup_files = [
        REPO_ROOT / "skills" / "CCteam-creator" / "references" / "mcp-setup.md",
        REPO_ROOT / "cn" / "skills" / "CCteam-creator-cn" / "references" / "mcp-setup.md",
    ]
    for path in mcp_setup_files:
        if not path.exists():
            warn(f"{path.relative_to(REPO_ROOT)}: not found, skip")
            continue
        text = path.read_text(encoding="utf-8")
        # npx pattern: "args": [..., "-y", "<pkg>", ...]
        for m in re.finditer(r'"-y"\s*,\s*"([^"]+)"', text):
            npm_packages.add(m.group(1))
        # uvx (PyPI) pattern: "command": "uvx", "args": ["<pkg>", ...]
        for m in re.finditer(r'"command":\s*"uvx",\s*"args":\s*\[\s*"([^"]+)"', text):
            pypi_packages.add(m.group(1))

    if not npm_packages and not pypi_packages:
        warn("No MCP package references found in mcp-setup.md — skip dep check")
        return

    def fetch_with_status(url, timeout=8):
        """Returns (body, http_code) tuple. body=None on non-2xx or transport failure."""
        try:
            result = subprocess.run(
                ["curl", "-s", "-m", str(timeout), "-w", "\n%{http_code}", url],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            return None, "curl-not-found"
        if result.returncode != 0:
            return None, f"curl-exit-{result.returncode}"
        body, _, http_code = result.stdout.rpartition("\n")
        return body, http_code

    for pkg in sorted(npm_packages):
        body, code = fetch_with_status(f"https://registry.npmjs.org/{pkg}")
        if code == "200" and body:
            try:
                ver = json.loads(body).get("dist-tags", {}).get("latest", "?")
                ok(f"npm '{pkg}' v{ver}")
            except Exception as e:
                warn(f"npm '{pkg}': returned 200 but body unparseable — {e}")
        elif code == "404":
            fail(f"npm '{pkg}': 404 — package does not exist on npm registry")
        else:
            warn(f"npm '{pkg}': {code} (network or registry issue?)")

    for pkg in sorted(pypi_packages):
        body, code = fetch_with_status(f"https://pypi.org/pypi/{pkg}/json")
        if code == "200" and body:
            try:
                ver = json.loads(body)["info"]["version"]
                ok(f"pypi '{pkg}' v{ver}")
            except Exception as e:
                warn(f"pypi '{pkg}': returned 200 but body unparseable — {e}")
        elif code == "404":
            fail(f"pypi '{pkg}': 404 — package does not exist on PyPI")
        else:
            warn(f"pypi '{pkg}': {code} (network or registry issue?)")


def main():
    print("=" * 60)
    print("CCteam-creator pre-release validation")
    print("=" * 60)
    print(f"Repo root: {REPO_ROOT}")
    if "--check-deps" not in sys.argv:
        print("(use --check-deps to also verify npm/PyPI package reachability)")

    check_versions()
    check_skill_variant(
        "EN skill (CCteam-creator)",
        REPO_ROOT / ".claude-plugin" / "plugin.json",
        REPO_ROOT / "skills" / "CCteam-creator",
        "CCteam-creator",
    )
    check_skill_variant(
        "CN skill (CCteam-creator-cn)",
        REPO_ROOT / "cn" / ".claude-plugin" / "plugin.json",
        REPO_ROOT / "cn" / "skills" / "CCteam-creator-cn",
        "CCteam-creator-cn",
    )
    check_parallel_structure()
    check_external_deps()

    print("\n" + "=" * 60)
    if errors:
        print(f"[FAIL] {len(errors)} error(s), {len(warnings_list)} warning(s)")
        print("")
        print("Do NOT push until all errors are fixed.")
        print("See docs/release-guide.md for details on each check.")
        sys.exit(1)
    elif warnings_list:
        print(f"[PASS with warnings] 0 errors, {len(warnings_list)} warning(s)")
        print("")
        print("You can push, but review warnings first.")
        sys.exit(0)
    else:
        print("[OK] All checks passed.")
        print("")
        print("Safe to commit and push.")
        sys.exit(0)


if __name__ == "__main__":
    main()
