#!/usr/bin/env bash
set -euo pipefail

# Bump version across all platform config files declared in .version-bump.json.
# Usage:
#   scripts/bump-version.sh <new-version>
#   scripts/bump-version.sh --check          # verify all versions match

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_ROOT/.version-bump.json"

RED='\033[91m'
GREEN='\033[92m'
RESET='\033[0m'

if [ ! -f "$CONFIG" ]; then
  printf "${RED}.version-bump.json not found${RESET}\n"
  exit 1
fi

# Extract file paths from config
get_paths() {
  python3 -c "
import json
cfg = json.load(open('$CONFIG'))
for f in cfg['files']:
    print(f['path'])
"
}

# Read version from a JSON file given a field spec like "version" or "plugins[0].version"
read_version() {
  local file="$1" field="$2"
  python3 -c "
import json
data = json.load(open('$REPO_ROOT/$file'))
parts = '$field'.replace(']', '').split('[')
obj = data
for p in parts:
    p2 = p.split('.')
    for k in p2:
        if k == '': continue
        if k.isdigit():
            obj = obj[int(k)]
        else:
            obj = obj[k]
print(obj)
"
}

# Write version into a JSON file
write_version() {
  local file="$1" field="$2" version="$3"
  python3 -c "
import json, pathlib
p = pathlib.Path('$REPO_ROOT/$file')
data = json.loads(p.read_text())
parts = '$field'.replace(']', '').split('[')
# navigate to parent, then set last key
obj = data
keys = []
for part in parts:
    for k in part.split('.'):
        if k: keys.append(int(k) if k.isdigit() else k)
parent = data
for k in keys[:-1]:
    parent = parent[k]
parent[keys[-1]] = '$version'
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
"
}

check_versions() {
  local versions=()
  local all_match=true

  while IFS= read -r path; do
    local field
    field="$(python3 -c "
import json
cfg = json.load(open('$CONFIG'))
for f in cfg['files']:
    if f['path'] == '$path':
        print(f['field'])
        break
")"
    local v
    v="$(read_version "$path" "$field")"
    printf "  %-40s %s\n" "$path" "$v"
    versions+=("$v")
  done < <(get_paths)

  local first="${versions[0]}"
  for v in "${versions[@]}"; do
    if [ "$v" != "$first" ]; then
      all_match=false
    fi
  done

  echo ""
  if [ "$all_match" = "true" ]; then
    printf "${GREEN}All versions match: %s${RESET}\n" "$first"
  else
    printf "${RED}Version mismatch detected!${RESET}\n"
    exit 1
  fi
}

bump_to() {
  local new_version="$1"

  # validate semver-ish format
  if ! [[ "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    printf "${RED}Invalid version format: %s (expected x.y.z)${RESET}\n" "$new_version"
    exit 1
  fi

  python3 -c "
import json
cfg = json.load(open('$CONFIG'))
for f in cfg['files']:
    print(f['path'] + '|' + f['field'])
" | while IFS='|' read -r path field; do
    write_version "$path" "$field" "$new_version"
    printf "  ${GREEN}Updated${RESET} %-40s → %s\n" "$path" "$new_version"
  done

  echo ""
  printf "${GREEN}Version bumped to %s${RESET}\n" "$new_version"
}

# ── CLI ────────────────────────────────────────────────────────────

case "${1:-}" in
  --check)
    echo "Checking version consistency:"
    echo ""
    check_versions
    ;;
  --help|-h|"")
    echo "Usage:"
    echo "  $(basename "$0") <new-version>   Bump all configs to new version"
    echo "  $(basename "$0") --check         Verify all versions match"
    ;;
  *)
    bump_to "$1"
    ;;
esac
