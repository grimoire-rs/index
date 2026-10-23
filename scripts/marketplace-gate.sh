#!/bin/sh
# Policy gate for a regenerated marketplace working tree.
#
# Run from inside the repository, after `grim update --marketplace` and
# `grim export marketplace`, and BEFORE `git add` or any commit. It reads git's
# own status (nothing is staged first) and refuses the run when a changed path
# is not something the export owns.
#
#   marketplace-gate.sh <manifest> <export.json>
#
# <manifest>     the marketplace manifest the run used (its directory is the
#                output root unless OUTPUT_ROOT is set; the lock is
#                `<stem>.lock` beside it)
# OUTPUT_ROOT    the export's -o directory, for a sibling deploy (vendored
#                from grimoire-rs/e2e-marketplace with this one change)
# <export.json>  the `grim export marketplace --format json` report
# MAX_FILE_BYTES  size cap per changed file (default 10485760)
#
# The allow-list is derived from the run, never from stored state:
#   - the manifest's lock path
#   - every `files[].path` of the report
#   - `<output root>/<client>/` for every `files[].client` (removed included)
#
# Exit: 0 clean (also when nothing changed), 1 policy violation, 2 bad input.
# Fails on: a path outside the allow-list, a symlink, a path whose `filter`
# attribute is `lfs`, a file over the size cap, a path containing a newline.
# POSIX sh; needs git, awk, sed, tr, wc. No jq, no bashisms (the GitLab
# component carries the same logic).
set -eu

die() {
    printf 'gate: %s\n' "$*" >&2
    exit 2
}

violations=0
fail() {
    printf 'gate: FAIL: %s\n' "$*" >&2
    violations=$((violations + 1))
}

[ "$#" -eq 2 ] || die "usage: marketplace-gate.sh <manifest> <export.json>"
manifest=$1
report=$2
max=${MAX_FILE_BYTES:-10485760}
case $max in
    '' | *[!0-9]*) die "MAX_FILE_BYTES must be a non-negative integer" ;;
esac
[ -f "$manifest" ] || die "manifest not found: $manifest"
[ -f "$report" ] || die "export report not found: $report"

abs_dir() { (cd "$1" 2>/dev/null && pwd -P); }

logical=$(pwd)
mdir=$(abs_dir "${OUTPUT_ROOT:-$(dirname "$manifest")}") || die "output root not found"
report=$(abs_dir "$(dirname "$report")")/$(basename "$report")
top=$(git rev-parse --show-toplevel) || die "not inside a git repository"
top=$(abs_dir "$top") || die "repository root not found"
cd "$top"

case $mdir in
    "$top") rel="" ;;
    "$top"/*) rel=${mdir#"$top"/}/ ;;
    *) die "manifest is outside the repository" ;;
esac
mbase=$(basename "$manifest")
lock="$rel${mbase%.*}.lock"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM
tab=$(printf '\t')

# One line per allowed thing: `E<path>` exact, `P<dir>/` prefix.
printf 'E%s\n' "$lock" >"$tmp/allow"
awk '
    /^[ \t]*"files"[ \t]*:[ \t]*\[/ { f = 1; next }
    f && /^[ \t]*"(client|path)"[ \t]*:[ \t]*"/ {
        key = $0; sub(/^[ \t]*"/, "", key); sub(/".*$/, "", key)
        val = $0; sub(/^[ \t]*"[a-z]+"[ \t]*:[ \t]*"/, "", val); sub(/",?[ \t]*$/, "", val)
        print key "\t" val
    }
' "$report" >"$tmp/files"

nfiles=0
while IFS=$tab read -r key val; do
    case $val in
        *\\* | *'"'*) die "unsupported character in the export report: $val" ;;
    esac
    case $key in
        client)
            case $val in
                '' | *[!a-z]*) die "malformed client in the export report: $val" ;;
            esac
            printf 'P%s%s/\n' "$rel" "$val" >>"$tmp/allow"
            ;;
        path)
            case $val in
                "$top"/*) p=${val#"$top"/} ;;
                "$logical"/*) p=${val#"$logical"/} ;;
                *) die "report path is outside the repository: $val" ;;
            esac
            case /$p/ in
                */../* | */./* | *//*) die "unnormalised report path: $val" ;;
            esac
            printf 'E%s\n' "$p" >>"$tmp/allow"
            nfiles=$((nfiles + 1))
            ;;
    esac
done <"$tmp/files"
[ "$nfiles" -gt 0 ] || die "no files[] entries in the export report (fail closed)"

git status --porcelain=v1 -z --untracked-files=all --no-renames >"$tmp/status.raw" ||
    die "git status failed"
if [ "$(tr -cd '\n' <"$tmp/status.raw" | wc -c)" -ne 0 ]; then
    fail "a changed path contains a newline"
fi
tr '\0' '\n' <"$tmp/status.raw" >"$tmp/status"
if [ ! -s "$tmp/status" ]; then
    echo "gate: nothing changed"
    [ "$violations" -eq 0 ] || exit 1
    exit 0
fi

: >"$tmp/paths"
changed=0
while IFS= read -r line; do
    case $line in
        ?? | ??' ') die "malformed status record: $line" ;;
        ??' '?*) ;;
        *) die "malformed status record: $line" ;;
    esac
    p=${line#???}
    changed=$((changed + 1))
    allowed=0
    while IFS= read -r a; do
        case $a in
            E*) [ "${a#E}" = "$p" ] && allowed=1 ;;
            P*)
                case $p in
                    "${a#P}"*) allowed=1 ;;
                esac
                ;;
        esac
    done <"$tmp/allow"
    [ "$allowed" -eq 1 ] || fail "path outside the allow-list: $p"
    if [ -L "$p" ]; then
        fail "symlink: $p"
    elif [ -f "$p" ]; then
        size=$(wc -c <"$p")
        [ "$size" -le "$max" ] || fail "file over $max bytes ($size): $p"
    fi
    printf '%s\n' "$p" >>"$tmp/paths"
done <"$tmp/status"

# `filter=lfs` from any attributes source (.gitattributes, info/attributes,
# global): an LFS pointer would commit a blob the export never wrote.
git check-attr filter --stdin <"$tmp/paths" >"$tmp/attr" || die "git check-attr failed"
while IFS= read -r line; do
    case $line in
        *': filter: lfs') fail "LFS-managed path: ${line%: filter: lfs}" ;;
    esac
done <"$tmp/attr"

if [ "$violations" -ne 0 ]; then
    printf 'gate: %d violation(s) in %d changed path(s)\n' "$violations" "$changed" >&2
    exit 1
fi
printf 'gate: ok, %d changed path(s) all within the allow-list\n' "$changed"
