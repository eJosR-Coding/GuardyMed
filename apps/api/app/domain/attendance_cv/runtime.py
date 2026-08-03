from __future__ import annotations

import hashlib
import math

from apps.api.app.domain.attendance_cv.entities import FaceEmbeddingResult, FaceVector


class DeterministicFaceEmbeddingRuntime:
    detector_name = "stub-face-detector"
    model_name = "stub-arcface-embedding"

    def embed(self, media_bytes: bytes) -> FaceEmbeddingResult:
        payload = media_bytes.strip()
        if len(payload) < 16:
            return FaceEmbeddingResult(
                face_detected=False,
                quality_score=0.0,
                embedding=None,
                detector_name=self.detector_name,
                model_name=self.model_name,
            )

        digest = hashlib.sha256(payload).digest()
        values = []
        for index in range(0, 32, 2):
            raw = int.from_bytes(digest[index : index + 2], byteorder="big", signed=False)
            values.append((raw / 65535.0) * 2.0 - 1.0)
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        normalized = tuple(value / magnitude for value in values)
        quality_score = min(1.0, max(0.2, len(payload) / 256.0))
        return FaceEmbeddingResult(
            face_detected=True,
            quality_score=quality_score,
            embedding=FaceVector(values=normalized),
            detector_name=self.detector_name,
            model_name=self.model_name,
        )
