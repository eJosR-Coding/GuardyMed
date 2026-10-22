#!/usr/bin/env python3
"""Evaluate GuardyMed's face verification on the public LFW test pairs.

Runs the same runtime code the API uses (``InsightFaceEmbeddingRuntime``) over the 1,000 labelled pairs
of Labeled Faces in the Wild (500 same person, 500 different people), then reports error rates at the
configured accept/review thresholds and a threshold sweep.

Nothing is downloaded into the repository: scikit-learn caches LFW under ``--data-home`` and InsightFace
caches its model weights under ``~/.insightface`` (override with ``GUARDYMED_ATTENDANCE_CV_MODEL_ROOT``).

    uv sync --extra cv
    uv run python scripts/evaluate_face_verification.py --output docs/evaluation/face_verification_lfw.json

Licences: LFW images are for non-commercial research use; the InsightFace ``buffalo_l`` weights are for
non-commercial research use only. See docs/AI_SERVICES.md.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def roc_auc(genuine: list[float], impostor: list[float]) -> float:
    """Probability that a random genuine score beats a random impostor score (ties count half)."""
    wins = 0.0
    for g in genuine:
        for i in impostor:
            wins += 1.0 if g > i else 0.5 if g == i else 0.0
    return wins / (len(genuine) * len(impostor))


def rates_at(threshold: float, genuine: list[float], impostor: list[float]) -> dict[str, float]:
    false_reject = sum(1 for score in genuine if score < threshold)
    false_accept = sum(1 for score in impostor if score >= threshold)
    return {
        "threshold": round(threshold, 4),
        "far": false_accept / len(impostor),
        "frr": false_reject / len(genuine),
    }


def equal_error_rate(genuine: list[float], impostor: list[float]) -> tuple[float, float]:
    best = (1.0, 0.0)
    for threshold in sorted(set(genuine) | set(impostor)):
        row = rates_at(threshold, genuine, impostor)
        gap = abs(row["far"] - row["frr"])
        if gap < best[0]:
            best = (gap, threshold)
    row = rates_at(best[1], genuine, impostor)
    return ((row["far"] + row["frr"]) / 2, best[1])


def load_pairs(data_home: Path, limit: int | None):
    from sklearn.datasets import fetch_lfw_pairs

    data = fetch_lfw_pairs(
        subset="test",
        data_home=str(data_home),
        color=True,
        slice_=(slice(0, 250), slice(0, 250)),  # the full 250x250 image, not the cropped default
        resize=1.0,
    )
    pairs, labels = data.pairs, data.target
    if limit:
        # keep the class balance when limiting
        half = limit // 2
        same = [i for i in range(len(labels)) if labels[i] == 1][:half]
        diff = [i for i in range(len(labels)) if labels[i] == 0][:half]
        keep = sorted(same + diff)
        pairs, labels = pairs[keep], labels[keep]
    return pairs, labels


def to_png_bytes(image) -> bytes:
    import cv2
    import numpy as np

    bgr = (np.clip(image, 0.0, 1.0) * 255).astype("uint8")[..., ::-1]
    ok, buffer = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("could not encode image")
    return buffer.tobytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-home", type=Path, default=REPO_ROOT / ".cache" / "lfw", help="where scikit-learn caches LFW")
    parser.add_argument("--limit", type=int, default=None, help="evaluate only N pairs (balanced), for a quick smoke run")
    parser.add_argument("--output", type=Path, default=None, help="write the JSON report here")
    parser.add_argument("--accept", type=float, default=None, help="accept threshold (default: GUARDYMED_ATTENDANCE_CV_ACCEPT_THRESHOLD)")
    parser.add_argument("--review", type=float, default=None, help="review threshold (default: GUARDYMED_ATTENDANCE_CV_REVIEW_THRESHOLD)")
    args = parser.parse_args()

    from apps.api.app.core.config import settings
    from apps.api.app.domain.attendance_cv.runtime import InsightFaceEmbeddingRuntime
    from apps.api.app.domain.attendance_cv.service import AttendanceCVService

    accept = args.accept if args.accept is not None else settings.attendance_cv_accept_threshold
    review = args.review if args.review is not None else settings.attendance_cv_review_threshold

    print("loading LFW test pairs ...", flush=True)
    pairs, labels = load_pairs(args.data_home, args.limit)
    print(f"{len(labels)} pairs ({int(labels.sum())} same person)", flush=True)

    runtime = InsightFaceEmbeddingRuntime(model_name=settings.attendance_cv_model_name, min_quality=settings.attendance_cv_min_quality, model_root=settings.attendance_cv_model_root)
    genuine: list[float] = []
    impostor: list[float] = []
    acquisition_failures = {"genuine": 0, "impostor": 0}
    started = time.time()
    for index, (pair, label) in enumerate(zip(pairs, labels, strict=True)):
        left = runtime.embed(to_png_bytes(pair[0]))
        right = runtime.embed(to_png_bytes(pair[1]))
        kind = "genuine" if label == 1 else "impostor"
        if left.embedding is None or right.embedding is None:
            acquisition_failures[kind] += 1  # the product would ask for a retake; excluded from the score distributions
            continue
        score = AttendanceCVService.cosine_similarity(left.embedding, right.embedding)
        (genuine if label == 1 else impostor).append(score)
        if (index + 1) % 100 == 0:
            print(f"  {index + 1}/{len(labels)} pairs", flush=True)
    elapsed = time.time() - started

    service = AttendanceCVService(threshold_accept=accept, threshold_review=review)

    def routing(scores: list[float]) -> dict[str, float]:
        counts = {"verified": 0, "needs_review": 0, "not_verified": 0}
        for score in scores:
            route = service.route_similarity(score)
            counts[{"accept": "verified", "review": "needs_review", "reject": "not_verified"}[route.value]] += 1
        return {key: value / len(scores) for key, value in counts.items()}

    far_hits = sum(1 for score in impostor if score >= accept)
    frr_hits = sum(1 for score in genuine if score < review)
    eer, eer_threshold = equal_error_rate(genuine, impostor)
    report = {
        "dataset": "LFW test pairs (scikit-learn fetch_lfw_pairs, subset=test)",
        "model": settings.attendance_cv_model_name,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "execution_provider": "CPUExecutionProvider"},
        "pairs": {"genuine": len(genuine), "impostor": len(impostor)},
        "acquisition_failures": acquisition_failures,
        "seconds_per_pair": round(elapsed / max(1, len(labels)), 3),
        "auc": round(roc_auc(genuine, impostor), 5),
        "equal_error_rate": round(eer, 5),
        "equal_error_threshold": round(eer_threshold, 4),
        "score_summary": {
            "genuine_mean": round(sum(genuine) / len(genuine), 4),
            "genuine_min": round(min(genuine), 4),
            "impostor_mean": round(sum(impostor) / len(impostor), 4),
            "impostor_max": round(max(impostor), 4),
        },
        "configured_thresholds": {
            "accept": accept,
            "review": review,
            "genuine_routing": routing(genuine),
            "impostor_routing": routing(impostor),
            # Wrongly auto-accepted impostors / wrongly auto-rejected genuine users, with 95% Wilson intervals.
            "false_accept_rate": {"value": far_hits / len(impostor), "ci95": wilson_interval(far_hits, len(impostor)), "count": far_hits},
            "false_reject_rate": {"value": frr_hits / len(genuine), "ci95": wilson_interval(frr_hits, len(genuine)), "count": frr_hits},
        },
        # Raw cosine scores (rounded) so the analysis can be redone without re-running the model.
        "scores": {"genuine": [round(x, 4) for x in genuine], "impostor": [round(x, 4) for x in impostor]},
        "sweep": [rates_at(t / 100, genuine, impostor) for t in range(10, 71, 5)],
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
