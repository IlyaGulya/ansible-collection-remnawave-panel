#!/bin/bash
set -e

echo "Running generator..."
uv run generate

if [ -n "$(git status --porcelain collection/)" ]; then
    echo "❌ Generated code is out of sync with generator/spec"
    echo "Run 'uv run generate' and commit the changes"
    echo ""
    echo "Changed files:"
    git status collection/
    echo ""
    echo "Diff:"
    git diff collection/
    exit 1
fi

echo "✅ Generated code is up to date"
