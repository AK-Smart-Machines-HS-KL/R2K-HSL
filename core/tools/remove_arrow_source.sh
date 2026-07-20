#!/bin/bash
# Removes the broken Apache Arrow apt source (unrelated to R2K-HSL).
# Silences the NO_PUBKEY 9E922B2D60E9FD1C warning on apt update.
set -e
SOURCE_FILE="/etc/apt/sources.list.d/apache-arrow.sources"
if [ -f "$SOURCE_FILE" ]; then
    echo "Removing $SOURCE_FILE ..."
    sudo rm "$SOURCE_FILE"
    sudo apt update
    echo "✅ Apache Arrow source removed, apt update clean."
else
    echo "Nothing to do: $SOURCE_FILE not present."
fi