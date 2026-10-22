// Thin fetch wrapper. Every API error has {detail, code}; validation errors also carry {fields}.
export class ApiError extends Error {
  constructor(message, { status = 0, code = "error", fields = [] } = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

const FRIENDLY = {
  face_not_detected: "No usable face was found in that image. Retake it facing the camera in good light.",
  face_low_quality: "The face is too unclear to use. Retake the photo in better light, facing the camera.",
  template_model_mismatch: "This enrolled face was captured with a different recognition model. Ask a manager to enroll it again.",
  media_too_large: "That image is too large (5 MB maximum).",
};

export async function api(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      credentials: "include",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Cannot reach the GuardyMed API. Is the server running?", { code: "network" });
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const code = data.code || "error";
    throw new ApiError(FRIENDLY[code] || data.detail || `Request failed (${response.status})`, {
      status: response.status,
      code,
      fields: data.fields || [],
    });
  }
  return data;
}

export const scheduling = (path, options) => api(`/scheduling${path}`, options);

export async function health() {
  try {
    const response = await fetch("/health");
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}
