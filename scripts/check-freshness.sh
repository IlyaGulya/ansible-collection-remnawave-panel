#!/bin/bash
set -e

echo "Running generator..."
uv run generate

COLLECTION_PATH="ansible_collections/remnawave/panel"

if [ -n "$(git status --porcelain "$COLLECTION_PATH/")" ]; then
    echo "❌ Generated code is out of sync with generator/spec"
    echo "Run 'uv run generate' and commit the changes"
    echo ""
    echo "Changed files:"
    git status "$COLLECTION_PATH/"
    echo ""
    echo "Diff:"
    git diff "$COLLECTION_PATH/"
    exit 1
fi

echo "✅ Generated code is up to date"
