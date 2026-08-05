const knownErrors = {
  "department code already exists": "Department code already exists. Create a different service code.",
  "worker document_id already exists": "Worker document ID already exists. Use a unique document number.",
  "schedule period already exists for department and month": "That month already exists for the selected department.",
  "worker does not belong to the schedule department": "That worker belongs to a different department than the selected period.",
  "worker already has an overlapping assignment": "That worker already has another assignment overlapping the same time window.",
  "schedule period must be draft to edit assignments": "Assignments can only be edited while the schedule period is still draft.",
  "schedule period must be approved before export": "Exports are available only after the period is approved.",
  "attendance enrollment already exists for worker": "That worker is already enrolled for attendance.",
  "worker must have an active attendance enrollment": "The worker is not enrolled for attendance yet.",
  "face enrollment not found for worker": "No face enrollment exists for this worker yet.",
  "face could not be extracted from media": "The image did not contain a usable face. Try a clearer, front-facing image.",
  "worker can only submit attendance for own assignments": "Workers can only submit attendance for their own assignments.",
  "worker can only access own attendance evidence": "Workers can only inspect their own attendance evidence.",
};

function humanizeErrorMessage(message) {
  const value = String(message || "").trim();
  return knownErrors[value] || value;
}

export async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, {
    credentials: "include",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(humanizeErrorMessage(data.detail || `${response.status} ${response.statusText}`));
  }
  return data;
}
