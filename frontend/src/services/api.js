import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8010/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Simple helper used by the Dashboard/health checks in Phase 1.
export async function checkHealth() {
  const { data } = await api.get("/health");
  return data;
}

// --- Papers (Phase 2) ---

export async function uploadPaper(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post("/papers/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded * 100) / event.total));
      }
    },
  });
  return data;
}

export async function listPapers() {
  const { data } = await api.get("/papers");
  return data;
}

export async function getPaper(paperId) {
  const { data } = await api.get(`/papers/${paperId}`);
  return data;
}

export async function analyzePaper(paperId) {
  const { data } = await api.post(`/papers/${paperId}/analyze`);
  return data;
}
