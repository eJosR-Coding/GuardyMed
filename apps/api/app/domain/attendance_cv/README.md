# Attendance CV domain

Owns:

- face enrollment template generation
- embedding-based verification
- similarity thresholds
- review routing

Does not own:

- scheduling truth
- attendance attempt persistence
- media uploads
- background jobs

The current implementation is a deterministic local scaffold.

It exists so the workflow and interfaces are stable before plugging in:

- OpenCV preprocessing
- ONNX Runtime inference
- InsightFace embeddings
