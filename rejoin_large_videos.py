#!/usr/bin/env python3
"""
rejoin_large_videos.py
Cross-platform binary assembler that scans parts_* directories or specific split directories,
concatenates chunks in sequence, and validates the reconstructed file against the source SHA-256 hash.
"""

import argparse
import glob
import hashlib
import json
import os
import sys


def compute_sha256(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def rejoin_directory(parts_dir, output_file=None):
    manifest_path = os.path.join(parts_dir, "split_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"Error: No split_manifest.json found in '{parts_dir}'.")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    source_file = manifest.get("source_file", "rejoined_video.mp4")
    expected_sha = manifest.get("sha256", "")
    parts = manifest.get("parts", [])

    if not output_file:
        output_file = os.path.join("3_Simulation/rawexport", source_file)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    print(f"Rejoining {len(parts)} parts from '{parts_dir}' into '{output_file}'...")

    with open(output_file, "wb") as f_out:
        for part_info in sorted(parts, key=lambda x: x["part_index"]):
            part_filename = part_info["file_name"]
            part_path = os.path.join(parts_dir, part_filename)

            if not os.path.exists(part_path):
                print(f"Error: Missing part file '{part_path}'. Aborting.")
                return False

            # Verify chunk sha
            part_sha = compute_sha256(part_path)
            if part_info.get("sha256") and part_sha != part_info["sha256"]:
                print(f"Error: Checksum mismatch on part '{part_filename}'.")
                return False

            with open(part_path, "rb") as f_in:
                while chunk := f_in.read(65536):
                    f_out.write(chunk)

            print(f"  -> Appended {part_filename} (verified)")

    reconstructed_sha = compute_sha256(output_file)
    print(f"Reconstruction finished. Output: {output_file}")
    print(f"Reconstructed SHA256: {reconstructed_sha}")

    if expected_sha and reconstructed_sha == expected_sha:
        print("SUCCESS: Checksum matches the original master file.")
        return True
    elif expected_sha:
        print("WARNING: Reconstructed file checksum does not match manifest!")
        return False
    return True


def scan_and_rejoin_all():
    part_dirs = glob.glob("parts_*")
    if not part_dirs:
        print("No parts_* directories found to rejoin.")
        return
    for pdir in part_dirs:
        rejoin_directory(pdir)


def main():
    parser = argparse.ArgumentParser(description="Rejoin split video chunks and verify SHA256 integrity.")
    parser.add_argument("parts_dir", nargs="?", default=None, help="Directory containing split parts and split_manifest.json")
    parser.add_argument("--out", "-o", default=None, help="Destination reconstructed video path")
    args = parser.parse_args()

    if args.parts_dir:
        rejoin_directory(args.parts_dir, args.out)
    else:
        scan_and_rejoin_all()


if __name__ == "__main__":
    main()
