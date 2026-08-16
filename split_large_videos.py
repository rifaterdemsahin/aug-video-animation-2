#!/usr/bin/env python3
"""
split_large_videos.py
Splits raw master video files exceeding 24MB into 24MB binary chunks to stay within GitHub repository size constraints.
Generates split_manifest.json with SHA-256 verification hashes for both the original file and each chunk.
"""

import argparse
import hashlib
import json
import os
import sys

CHUNK_SIZE = 24 * 1024 * 1024  # 25,165,824 bytes (24MB)


def compute_sha256(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def split_video(file_path, output_dir=None):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return False

    file_size = os.path.getsize(file_path)
    base_name = os.path.basename(file_path)
    file_stem, _ = os.path.splitext(base_name)

    if output_dir is None:
        output_dir = f"parts_{file_stem}"

    os.makedirs(output_dir, exist_ok=True)
    orig_hash = compute_sha256(file_path)

    print(f"Splitting '{file_path}' ({file_size} bytes, SHA256: {orig_hash[:12]}...)")
    parts = []
    chunk_index = 0

    with open(file_path, "rb") as f_in:
        while True:
            chunk_data = f_in.read(CHUNK_SIZE)
            if not chunk_data:
                break
            part_filename = f"{file_stem}.part{chunk_index:03d}"
            part_path = os.path.join(output_dir, part_filename)

            part_sha = hashlib.sha256(chunk_data).hexdigest()
            with open(part_path, "wb") as f_out:
                f_out.write(chunk_data)

            parts.append({
                "part_index": chunk_index,
                "file_name": part_filename,
                "size_bytes": len(chunk_data),
                "sha256": part_sha
            })
            print(f"  -> Created part {chunk_index}: {part_filename} ({len(chunk_data)} bytes)")
            chunk_index += 1

    manifest = {
        "source_file": base_name,
        "total_bytes": file_size,
        "chunk_size": CHUNK_SIZE,
        "total_parts": len(parts),
        "sha256": orig_hash,
        "parts": parts
    }

    manifest_path = os.path.join(output_dir, "split_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f_man:
        json.dump(manifest, f_man, indent=2)

    print(f"Split completed. Manifest saved to '{manifest_path}'. Total parts: {len(parts)}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Split videos >24MB into GitHub-compliant chunks.")
    parser.add_argument("video_path", nargs="?", default="3_Simulation/rawexport/sample_raw_master.mp4", help="Path to video file")
    parser.add_argument("--out", "-o", default=None, help="Output directory for parts")
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Target video '{args.video_path}' does not exist. Creating a placeholder test file...")
        os.makedirs(os.path.dirname(args.video_path) or ".", exist_ok=True)
        with open(args.video_path, "wb") as f:
            # Create a 25MB test file
            f.write(b"0" * (25 * 1024 * 1024))
        print(f"Created dummy test file at {args.video_path}")

    split_video(args.video_path, args.out)


if __name__ == "__main__":
    main()
