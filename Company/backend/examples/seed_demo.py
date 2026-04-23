"""
Seed the in-memory leaderboard with a simple demo using public endpoints.

This script:
  - Fetches a few source sentences from the Spanish demo dataset
  - Submits two model runs with slightly different outputs
  - Prints the leaderboard response

Run:
  export LEADERBOARD_API_BASE="http://localhost:5001"
  python backend/examples/seed_demo.py

Make sure the backend is running on port 5001:
  export PORT=5001 FLASK_ENV=development
  python backend/app.py
"""

from __future__ import annotations
import os
from typing import List

try:
    from backend.sdk.leaderboard_sdk import LeaderboardClient
except Exception:
    # Fallback for running from project root
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from sdk.leaderboard_sdk import LeaderboardClient  # type: ignore


def slightly_worse(sentences: List[str]) -> List[str]:
    # Produce a slightly perturbed copy to score lower than exact copy
    out = []
    for s in sentences:
        if len(s.split()) > 3:
            parts = s.split()
            parts = parts[:-1]  # drop last token
            out.append(" ".join(parts))
        else:
            out.append(s.lower())
    return out


def main() -> None:
    base = os.getenv("LEADERBOARD_API_BASE", "http://localhost:5001")
    client = LeaderboardClient(base_url=base)

    # Pull demo source sentences (these align with internal reference translations for demo)
    src = client.get_source_sentences(dataset_name="flores_spanish_translation", count=3, start_idx=0)
    sentence_ids = src["sentence_ids"]
    source_sentences = src["source_sentences"]

    # Model A: copies the sentences exactly (should get a high BLEU)
    res_a = client.submit_model(
        benchmark_dataset_name="flores_spanish_translation",
        model_name="demo-model-exact",
        model_results=source_sentences,
        sentence_ids=sentence_ids,
    )
    print("Submitted demo-model-exact:", res_a)

    # Model B: slightly perturbed output (lower BLEU)
    res_b = client.submit_model(
        benchmark_dataset_name="flores_spanish_translation",
        model_name="demo-model-perturbed",
        model_results=slightly_worse(source_sentences),
        sentence_ids=sentence_ids,
    )
    print("Submitted demo-model-perturbed:", res_b)

    # Read current leaderboard
    lb = client.get_leaderboard()
    print("\nLeaderboard:")
    for row in lb.get("leaderboard", []):
        print(f"  {row['rank']}. {row['model_name']} — {row['dataset_name']} — score={row['score']:.4f}")


if __name__ == "__main__":
    main()

