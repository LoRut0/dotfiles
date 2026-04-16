#!/usr/bin/env bash
set -euo pipefail

DEST_DIR="/home/loruto/.local/share/v2rayN/bin/"
TMP_DIR="$(mktemp -d)"
LOG_TAG="update-v2ray-geo"

GEOSITE_URL="https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat"
GEOIP_URL="https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat"

GEOSITE_SHA_URL="https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat.sha256sum"
GEOIP_SHA_URL="https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat.sha256sum"

mkdir -p "$DEST_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

log() {
    echo "[$LOG_TAG] $*"
    logger -t "$LOG_TAG" -- "$*"
}

download_with_fallback() {
    local url="$1"
    local out="$2"

    # 1. HTTP proxy
    if curl -fsSL --connect-timeout 15 --max-time 300 \
        --proxy "http://127.0.0.1:10808" \
        -o "$out" "$url"; then
        return 0
    fi

    # 2. SOCKS5 proxy
    if curl -fsSL --connect-timeout 15 --max-time 300 \
        --proxy "socks5h://127.0.0.1:10808" \
        -o "$out" "$url"; then
        return 0
    fi

    # 3. Direct
    curl -fsSL --connect-timeout 15 --max-time 300 \
        -o "$out" "$url"
}

extract_expected_hash() {
    local sha_file="$1"
    awk '{print $1}' "$sha_file" | tr -d '\r\n'
}

local_hash() {
    local file="$1"
    sha256sum "$file" | awk '{print $1}'
}

update_one() {
    local name="$1"
    local file_url="$2"
    local sha_url="$3"

    local dest_file="$DEST_DIR/$name"
    local remote_sha_file="$TMP_DIR/$name.sha256sum"
    local tmp_file="$TMP_DIR/$name"

    log "Checking hash for $name ..."
    download_with_fallback "$sha_url" "$remote_sha_file"

    local expected_hash
    expected_hash="$(extract_expected_hash "$remote_sha_file")"

    if [[ -z "$expected_hash" ]]; then
        log "Failed to parse remote hash for $name"
        return 1
    fi

    if [[ -f "$dest_file" ]]; then
        local current_hash
        current_hash="$(local_hash "$dest_file")"
        if [[ "$current_hash" == "$expected_hash" ]]; then
            log "$name is up to date, skipping"
            return 0
        fi
    fi

    log "Downloading $name ..."
    download_with_fallback "$file_url" "$tmp_file"

    local downloaded_hash
    downloaded_hash="$(local_hash "$tmp_file")"

    if [[ "$downloaded_hash" != "$expected_hash" ]]; then
        log "Checksum mismatch for $name: expected $expected_hash, got $downloaded_hash"
        return 1
    fi

    install -m 0644 "$tmp_file" "$dest_file"
    log "$name updated successfully"
}

update_one "geosite.dat" "$GEOSITE_URL" "$GEOSITE_SHA_URL"
update_one "geoip.dat" "$GEOIP_URL" "$GEOIP_SHA_URL"

log "All done"
