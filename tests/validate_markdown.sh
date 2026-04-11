#!/usr/bin/env bash
# Structural validation for a markdown file.
# Usage: validate_markdown.sh <file> <required-section-header-1> [<required-section-header-2> ...]
# Exits 0 if all required headers are found, 1 otherwise.

set -e

if [ "$#" -lt 2 ]; then
  echo "validate_markdown: usage: $0 <file> <required-header> [<required-header>...]" >&2
  exit 1
fi

FILE="$1"
shift

if [ ! -f "$FILE" ]; then
  echo "validate_markdown: file not found: $FILE" >&2
  exit 1
fi

missing=0
for header in "$@"; do
  if ! grep -qF "$header" "$FILE"; then
    echo "validate_markdown: missing header '$header' in $FILE" >&2
    missing=$((missing + 1))
  fi
done

if [ "$missing" -gt 0 ]; then
  exit 1
fi
