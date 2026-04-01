"""
Seed Qdrant with past approved copy examples.

This is what makes the 80/20 learned-vs-prompted split work from day one.
Without seeds, the first few weeks will be 100% prompt-driven until real
approved outputs accumulate.

Input format — JSONL file, one JSON object per line:
    {"text": "...", "channel": "linkedin", "campaign": "series_a", "approved_at": "2025-01-15"}

Usage:
    python -m scripts.seed_brand_memory --input ./brand_seeds/approved_copy.jsonl
    python -m scripts.seed_brand_memory --input ./brand_seeds/approved_copy.jsonl --dry-run
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path


async def seed(input_path: Path, dry_run: bool) -> None:
    # Import here so config is loaded from .env before any module-level code
    from zeta_ima.memory.brand import ensure_collection, save_approved_output

    ensure_collection()

    lines = input_path.read_text().strip().splitlines()
    print(f"Loading {len(lines)} examples from {input_path}")

    success = 0
    errors = 0
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  [line {i}] JSON parse error: {e}")
            errors += 1
            continue

        text = record.get("text", "").strip()
        if not text:
            print(f"  [line {i}] Skipping — missing 'text' field")
            errors += 1
            continue

        metadata = {
            "output_id": record.get("id") or str(uuid.uuid4()),
            "user_id": record.get("user_id", "seed"),
            "campaign_id": record.get("campaign"),
            "brief": record.get("brief", ""),
            "channel": record.get("channel", "unknown"),
            "approved_at": record.get("approved_at", ""),
            "iterations_needed": record.get("iterations_needed", 1),
        }

        if dry_run:
            print(f"  [line {i}] DRY RUN — would save: {text[:80]}...")
        else:
            try:
                point_id = await save_approved_output(text, metadata)
                print(f"  [line {i}] Saved → Qdrant point {point_id}")
                success += 1
            except Exception as e:
                print(f"  [line {i}] Error saving: {e}")
                errors += 1

    print(f"\nDone. {success} saved, {errors} errors.")


def main():
    parser = argparse.ArgumentParser(description="Seed Qdrant brand memory with approved copy examples.")
    parser.add_argument("--input", required=True, type=Path, help="Path to JSONL input file")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be saved without writing")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} does not exist.")
        sys.exit(1)

    asyncio.run(seed(args.input, args.dry_run))


if __name__ == "__main__":
    main()
