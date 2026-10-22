# AI services

GuardyMed has one AI feature, **face verification for attendance**. This page says what it does, how it was measured,
and where it should not be trusted. Planned AI work (document intelligence, assistant) is not implemented; see the
[roadmap](ROADMAP.md).

## How verification works

1. **Enrollment** (manager). A photo is decoded, a face is detected, and a 512-number embedding is computed and stored
   as the worker's template. The image itself is discarded. A photo without a usable face is rejected, and nothing is stored.
2. **Check-in** (worker). A capture goes through the same steps; the cosine similarity between the capture and the
   template is routed with two thresholds:

   | Similarity | Outcome (API `route`) | Result |
   | --- | --- | --- |
   | `>= 0.45` | `verified` (`accept`) | attempt accepted automatically, decided by `system_cv` |
   | `>= 0.25` and `< 0.45` | `needs_review` (`review`) | attempt stays pending for a manager |
   | `< 0.25` | `not_verified` (`reject`) | attempt rejected automatically |

3. **Guards.** No face or low detector confidence (< 0.5): HTTP 422, no attempt is recorded, the worker retries. More than one
   face visible: an otherwise "verified" result is downgraded to `needs_review` with the reason stored. A template made by a
   different model than the active one: HTTP 409 `template_model_mismatch` (re-enroll). Images larger than 5 MB: HTTP 413.
4. **Audit.** Every attempt stores similarity, both thresholds, detector and model names; enrollment and every decision
   appear in the activity log. Manual check-ins (no camera) are a separate, always-pending path.

Thresholds are environment variables: `GUARDYMED_ATTENDANCE_CV_ACCEPT_THRESHOLD`, `GUARDYMED_ATTENDANCE_CV_REVIEW_THRESHOLD`,
`GUARDYMED_ATTENDANCE_CV_MIN_QUALITY`.

## Runtimes

| | Demo runtime (`stub`, default) | Real runtime (`insightface`) |
| --- | --- | --- |
| Dependencies | none | `uv sync --extra cv` (NumPy, OpenCV headless, ONNX Runtime, InsightFace) |
| Recognises faces | **No.** Hashes the bytes; identical bytes match, anything else does not | Yes: SCRFD detector + ResNet-50 ArcFace (`buffalo_l`), CPU |
| Purpose | Show the workflow and all three outcomes without ML packages | Actual verification |
| Demo captures | `GMDEMO:<identity>:<cosine>` payloads produce a chosen similarity (used by the UI's sample buttons) | not used |

The UI labels the demo runtime wherever a result appears ("Simulated"). If `insightface` is requested but cannot start
(missing extra, blocked download, unsupported platform), the app falls back to the demo runtime and says so in the Attendance
screen and in `GET /api/v1/scheduling/attendance/cv/status` (`fallback_reason`).

Model weights are fetched on first use into `~/.insightface` (set `GUARDYMED_ATTENDANCE_CV_MODEL_ROOT` to move them) and are
never committed.

## Evaluation

`scripts/evaluate_face_verification.py` runs the production runtime over the 1,000 labelled pairs of the LFW test split
(500 same person, 500 different), via scikit-learn's `fetch_lfw_pairs` at full 250x250 resolution. Results are in
[`docs/evaluation/face_verification_lfw.json`](evaluation/face_verification_lfw.json), including the raw scores.

```bash
uv sync --extra cv && make eval
```

Environment: Python 3.12.13, CPU only, about 0.58 s per pair (two images, including PNG decoding).

**Result.** 492 same-person and 497 different-person pairs were scored;
11 of 1,000 pairs had a face that could not be extracted
(the product would ask for a retake) and are excluded.

- AUC **0.981**; equal error rate **3.8%** (at similarity 0.12).
- Mean similarity: same person 0.66, different people 0.00;
  highest different-person score 0.20.
- At the shipped thresholds (accept 0.45, review 0.25):
  - different-person pairs wrongly **verified**: **0 of 497**
    (95% upper bound 0.77%);
  - same-person pairs: **94.9% verified**,
    0.8% sent to review,
    **4.3% not verified** (false reject, the worker retries or a manager overrides).

Threshold sweep (error rates among the scored pairs):

| Threshold | False accept | False reject |
| --- | --- | --- |
| 0.15 | 1.4% | 3.9% |
| 0.20 | 0.0% | 4.1% |
| 0.25 | 0.0% | 4.3% |
| 0.30 | 0.0% | 4.3% |
| 0.35 | 0.0% | 4.5% |
| 0.40 | 0.0% | 4.9% |
| 0.45 | 0.0% | 5.1% |
| 0.50 | 0.0% | 6.9% |
| 0.55 | 0.0% | 11.2% |
| 0.60 | 0.0% | 20.1% |

### How to read this

- **The thresholds were chosen after looking at this same data**, so the false-accept figure is optimistic. A fair estimate
  needs a held-out set, ideally images from the real deployment.
- 497 impostor pairs can only show that the false-accept rate is probably below about 0.8%. A claim like "one in a thousand"
  needs thousands of impostor pairs.
- The 4% of same-person pairs that score below 0.25 are mostly hard cases (extreme pose, age gaps, occlusion) and a few
  label problems that are known in LFW. The review band is nearly unused on this dataset because scores are bimodal; it exists
  for real-world conditions (lighting, masks, glasses) that LFW does not cover.
- LFW is frontal-ish celebrity web photos. A hospital corridor camera, scrubs, masks and tired faces are harder. Expect worse
  numbers there and measure them before relying on this.
- **No liveness detection.** The evaluation measures identity matching only; a photo or screen of an enrolled person is not tested and would pass.
- The demo runtime is not evaluated: it does not recognise faces.

## Privacy and licences

- Face embeddings are biometric personal data. They are stored in the database as JSON; images are not stored. Treat the database
  accordingly, and check local law (for example consent and retention rules) before using this with real staff.
- **InsightFace**: the code is MIT-licensed, but the pretrained `buffalo_l` weights are provided for **non-commercial research use only**.
  Commercial use needs a licence from the InsightFace authors or different weights.
- **LFW** (Labeled Faces in the Wild) is for research use; images are downloaded by the evaluation script into `.cache/`
  (git-ignored) and never redistributed from this repository.
