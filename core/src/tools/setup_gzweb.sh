#!/bin/bash
# setup_gzweb.sh -- GZWeb (Gazebo Classic web client) setup for the ROS2K GUI.
# Gate 1 PoC validated 2026-08-26 (see docs/gui_v67_discussion.md ANNEX N4).
#
# Run INSIDE the gazebo container:
#   docker exec core_gazebo bash /workspace/tools/setup_gzweb.sh
#
# Idempotent: skips clone/patch when already applied; re-runs deploy only
# when the bundle is missing.
#
# What it does:
#   1. apt deps (nodejs, npm, libjansson-dev, imagemagick) -- cheap, also in Dockerfile
#   2. clone osrf/gzweb (GZWeb 1.3.0, commit 93b6a6f) to /opt/gzweb
#   3. apply the inline-material patch (ROS2K worlds use SDF <ambient>/<diffuse>
#      without material scripts -- upstream gzweb renders those WHITE)
#   4. ./deploy.sh -m local  (npm install + grunt concat + cmake gzbridge +
#      node-gyp + local model DB; ~10 min first run)
#
# After setup, start the server (gzserver must be running first):
#   docker exec -d core_gazebo bash -c 'cd /opt/gzweb/gzbridge && ./server.js 8080'
# Then open http://localhost:8080

set -euo pipefail

GZWEB_DIR=/opt/gzweb
GZWEB_REPO=https://github.com/osrf/gzweb
PATCH_FILE=/workspace/tools/gzweb_inline_material.patch

# --- 1. apt dependencies (fast no-op when present) -------------------------
if ! command -v npm >/dev/null 2>&1 || ! dpkg -s libjansson-dev >/dev/null 2>&1 \
   || ! command -v convert >/dev/null 2>&1; then
    echo "[gzweb] installing apt deps (nodejs npm libjansson-dev imagemagick)..."
    apt-get update -qq
    apt-get install -y -qq nodejs npm libjansson-dev imagemagick
else
    echo "[gzweb] apt deps present"
fi

# --- 2. clone ---------------------------------------------------------------
if [ ! -d "$GZWEB_DIR/.git" ]; then
    echo "[gzweb] cloning $GZWEB_REPO ..."
    git clone --depth 1 "$GZWEB_REPO" "$GZWEB_DIR"
else
    echo "[gzweb] clone present"
fi
cd "$GZWEB_DIR"

# --- 3. inline-material patch ------------------------------------------------
if grep -q "ROS2K patch" gz3d/src/gziface.js; then
    echo "[gzweb] inline-material patch already applied"
else
    echo "[gzweb] applying inline-material patch..."
    patch -p1 --forward < "$PATCH_FILE"
fi

# --- 4. build (skip when the patched bundle is deployed) ---------------------
if [ -f http/client/gz3d.gui.js ] && grep -q "ROS2K patch" http/client/gz3d.gui.js \
   && [ -f gzbridge/build/Debug/gzbridge.node ]; then
    echo "[gzweb] build present (patched bundle + gzbridge.node)"
else
    echo "[gzweb] running deploy (npm install, grunt, cmake, node-gyp)..."
    # ROS setup.bash references unbound vars (AMENT_TRACE_SETUP_FILES) —
    # temporarily disable `set -u` (from the shebang `set -euo pipefail`)
    set +u
    source /opt/ros/humble/setup.bash
    set -u
    export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models
    ./deploy.sh -m local
    # deploy.sh runs `grunt build` (concat+jshint+uglify); the deployed client
    # bundle is the unminified concat -- make sure it carries the patch.
    if ! grep -q "ROS2K patch" http/client/gz3d.gui.js; then
        ./node_modules/.bin/grunt concat
        cp gz3d/build/gz3d.gui.js http/client/gz3d.gui.js
    fi
fi

echo "[gzweb] OK -- start with: docker exec -d core_gazebo bash -c 'cd /opt/gzweb/gzbridge && ./server.js 8080'"
