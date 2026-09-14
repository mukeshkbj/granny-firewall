#!/usr/bin/env bash
# Convert any audio file to PCM16 WAV (24kHz mono) — best quality path.
# Requires ffmpeg (brew install ffmpeg). Not required: the app decodes
# wav/mp3/flac/ogg via soundfile and resamples internally.
set -euo pipefail
in="$1"; out="${2:-samples/$(basename "${in%.*}").wav}"
mkdir -p samples
ffmpeg -y -i "$in" -ar 24000 -ac 1 -f wav "$out"
echo "wrote $out"
