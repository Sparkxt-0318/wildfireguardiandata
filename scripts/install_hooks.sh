#!/bin/sh
cp "$(git rev-parse --show-toplevel)/scripts/pre-commit" "$(git rev-parse --git-dir)/hooks/pre-commit"
chmod +x "$(git rev-parse --git-dir)/hooks/pre-commit"
echo "pre-commit key check installed"
