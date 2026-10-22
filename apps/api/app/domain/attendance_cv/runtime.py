"""Face embedding runtimes.

Two implementations share one protocol:

* ``DeterministicFaceEmbeddingRuntime`` ("stub") needs no ML dependencies. It does **not** recognise
  faces: it hashes the uploaded bytes (identical bytes -> identical embedding) and understands a tiny
  simulation protocol, ``GMDEMO:<identity>:<cosine>``, so the demo can show all three outcomes.
* ``InsightFaceEmbeddingRuntime`` runs the real detector + ArcFace-style recogniser through ONNX Runtime.
"""

from __future__ import annotations

import hashlib
import math
import random

from apps.api.app.domain.attendance_cv.entities import FaceEmbeddingResult, FaceVector

STUB_DIMENSIONS = 64
DEMO_PREFIX = b"GMDEMO:"


def _unit(values: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / magnitude for value in values]


def _seeded_vector(seed: str) -> list[float]:
    rng = random.Random(hashlib.sha256(seed.encode("utf-8")).digest())
    return _unit([rng.gauss(0.0, 1.0) for _ in range(STUB_DIMENSIONS)])


def demo_capture(identity: str, cosine: float = 1.0) -> bytes:
    """Bytes the stub runtime reads as "a capture of ``identity`` whose cosine to the enrolled template is ``cosine``"."""
    return DEMO_PREFIX + f"{identity}:{cosine:.4f}".encode("ascii")


def _demo_embedding(identity: str, cosine: float) -> list[float]:
    base = _seeded_vector(identity)
    noise = _seeded_vector(f"{identity}#{cosine:.4f}")
    projection = sum(a * b for a, b in zip(noise, base, strict=True))
    orthogonal = _unit([n - projection * b for n, b in zip(noise, base, strict=True)])
    sine = math.sqrt(max(0.0, 1.0 - cosine * cosine))
    return [cosine * b + sine * o for b, o in zip(base, orthogonal, strict=True)]


class DeterministicFaceEmbeddingRuntime:
    kind = "stub"
    is_demo = True
    detector_name = "stub-detector"
    model_name = "stub-simulated-embedding"

    def embed(self, media_bytes: bytes) -> FaceEmbeddingResult:
        payload = media_bytes.strip()
        if payload.startswith(DEMO_PREFIX):
            try:
                identity, cosine_text = payload[len(DEMO_PREFIX) :].decode("ascii").rsplit(":", 1)
                cosine = min(1.0, max(-1.0, float(cosine_text)))
            except (UnicodeDecodeError, ValueError):
                return self._failure("image_unreadable")
            return self._success(_demo_embedding(identity, cosine), quality=0.95)
        if len(payload) < 16:
            return self._failure("no_face")
        digest = hashlib.sha256(payload).digest()
        rng = random.Random(digest)
        quality = min(1.0, max(0.2, len(payload) / 256.0))
        return self._success(_unit([rng.gauss(0.0, 1.0) for _ in range(STUB_DIMENSIONS)]), quality=quality)

    def _success(self, values: list[float], *, quality: float) -> FaceEmbeddingResult:
        return FaceEmbeddingResult(
            face_detected=True,
            quality_score=quality,
            embedding=FaceVector(values=tuple(values)),
            detector_name=self.detector_name,
            model_name=self.model_name,
        )

    def _failure(self, reason: str) -> FaceEmbeddingResult:
        return FaceEmbeddingResult(
            face_detected=False,
            quality_score=0.0,
            embedding=None,
            detector_name=self.detector_name,
            model_name=self.model_name,
            failure=reason,
            face_count=0,
        )


class InsightFaceEmbeddingRuntime:
    kind = "insightface"
    is_demo = False
    detector_name = "insightface-retinaface"

    def __init__(self, *, model_name: str = "buffalo_l", min_quality: float = 0.5, model_root: str | None = None) -> None:
        try:
            import cv2
            import numpy as np
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise RuntimeError("insightface runtime dependencies are not installed (install the `cv` extra)") from exc

        self._cv2 = cv2
        self._np = np
        self.model_name = model_name
        self.min_quality = min_quality
        # Detection + recognition only: landmarks and gender/age models are not needed and slow start-up.
        self._app = FaceAnalysis(
            name=model_name,
            root=model_root or "~/.insightface",
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        self._app.prepare(ctx_id=-1, det_size=(640, 640))

    def embed(self, media_bytes: bytes) -> FaceEmbeddingResult:
        image = self._cv2.imdecode(self._np.frombuffer(media_bytes, dtype=self._np.uint8), self._cv2.IMREAD_COLOR)
        if image is None:
            return self._failure("image_unreadable")

        faces = self._app.get(image)
        if not faces:
            return self._failure("no_face")

        face = max(faces, key=lambda item: (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]))
        quality = float(getattr(face, "det_score", 0.0))
        embedding = getattr(face, "embedding", None)
        if embedding is None:
            return self._failure("no_face")
        if quality < self.min_quality:
            return self._failure("low_quality", quality=quality, face_count=len(faces))

        values = _unit([float(value) for value in embedding.tolist()])
        return FaceEmbeddingResult(
            face_detected=True,
            quality_score=quality,
            embedding=FaceVector(values=tuple(values)),
            detector_name=self.detector_name,
            model_name=self.model_name,
            face_count=len(faces),
        )

    def _failure(self, reason: str, *, quality: float = 0.0, face_count: int = 0) -> FaceEmbeddingResult:
        return FaceEmbeddingResult(
            face_detected=False,
            quality_score=quality,
            embedding=None,
            detector_name=self.detector_name,
            model_name=self.model_name,
            failure=reason,
            face_count=face_count,
        )
