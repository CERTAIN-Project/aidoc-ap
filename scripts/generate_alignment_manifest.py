#!/usr/bin/env python3
"""Generate a manifest of all alignment TTL files in docs/resources/"""
import json
from pathlib import Path

RESOURCES_DIR = Path("docs/resources")
OUTPUT_FILE = RESOURCES_DIR / "alignments-manifest.json"

def main():
    alignment_files = sorted(RESOURCES_DIR.glob("*-alignments.ttl"))
    
    manifest = {
        "files": [f"resources/{f.name}" for f in alignment_files],
        "count": len(alignment_files),
        "generated": "auto"
    }
    
    OUTPUT_FILE.write_text(json.dumps(manifest, indent=2))
    print(f"✓ Generated manifest with {len(alignment_files)} alignment files")
    print(f"  → {OUTPUT_FILE}")
    for f in alignment_files:
        print(f"    - {f.name}")

if __name__ == "__main__":
    main()
