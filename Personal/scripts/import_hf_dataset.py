#!/usr/bin/env python3
"""
Import a Hugging Face dataset into the leaderboard DB (GLUE SST-2 recipe first).

Run from repo root:
  cd Personal && PYTHONPATH=. python scripts/import_hf_dataset.py \\
    --dataset nyu-mll/glue --config sst2 --split validation \\
    --dataset-id hf_glue_sst2_validation --limit 200

Use --limit 0 for the full split (all rows with valid labels).

More recipes (config is usually `default`):
  --dataset squad --config default --split validation --dataset-id hf_squad_validation
  --dataset conll2003 --config default --split validation --dataset-id hf_conll2003_validation
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import HF dataset into leaderboard DB")
    parser.add_argument("--dataset", required=True, help='HF dataset id, e.g. "nyu-mll/glue"')
    parser.add_argument("--config", default="default", help='Subset, e.g. "sst2"')
    parser.add_argument("--split", default="validation", help="Split name (validation recommended for SST-2)")
    parser.add_argument("--dataset-id", dest="dataset_id", default=None, help="Leaderboard Dataset.id (PK)")
    parser.add_argument("--name", dest="display_name", default=None, help="Display name")
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max rows (0 = entire split for registered recipes)",
    )
    args = parser.parse_args()

    os.chdir(ROOT)

    from database import init_db, SessionLocal
    from hf_importer import HuggingFaceImporter
    from dataset_import import persist_imported_dataset, DatasetImportError

    init_db()
    # recipe_limit 0 => full split (see HuggingFaceImporter.import_dataset_with_options)
    recipe_limit = 0 if args.limit == 0 else args.limit
    importer = HuggingFaceImporter()
    payload = importer.import_dataset_with_options(
        args.dataset,
        args.config,
        args.split,
        num_samples=args.limit if args.limit > 0 else 100,
        leaderboard_dataset_id=args.dataset_id,
        display_name=args.display_name,
        recipe_limit=recipe_limit,
    )
    if not payload:
        print("Import failed.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        try:
            ds = persist_imported_dataset(db, payload)
        except DatasetImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"OK dataset_id={ds.id} name={ds.name!r} num_examples={ds.num_examples}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
