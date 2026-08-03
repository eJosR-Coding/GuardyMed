from __future__ import annotations

from typing import Protocol

from apps.api.app.domain.attendance_cv.entities import FaceEmbeddingResult


class FaceEmbeddingRuntime(Protocol):
    detector_name: str
    model_name: str

    def embed(self, media_bytes: bytes) -> FaceEmbeddingResult: ...
