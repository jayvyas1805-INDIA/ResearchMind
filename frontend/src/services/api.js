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

// --- Search (Phase 5) ---

export async function searchPaper(paperId, query, topK, useHybrid) {
  const { data } = await api.post(`/papers/${paperId}/search`, {
    query,
    top_k: topK || undefined,
    use_hybrid: !!useHybrid,
  });
  return data;
}

// --- Chat / RAG (Phase 6) ---

export async function askPaper(paperId, question) {
  const { data } = await api.post(`/papers/${paperId}/chat`, { question });
  return data;
}

// --- Summary (Phase 7) ---

export async function getSummary(paperId) {
  const { data } = await api.get(`/papers/${paperId}/summary`);
  return data;
}

export async function regenerateSummary(paperId) {
  const { data } = await api.post(`/papers/${paperId}/summary`);
  return data;
}

// --- Comparison (Phase 8) ---

export async function comparePapers(paperId1, paperId2) {
  const { data } = await api.post(`/papers/compare`, {
    paper_id_1: paperId1,
    paper_id_2: paperId2,
  });
  return data;
}

// --- Settings (Phase 9) ---

export async function getSettings() {
  const { data } = await api.get(`/settings`);
  return data;
}

// --- Leaderboard (cross-paper results) ---

export async function getLeaderboard(filters = {}) {
  const params = new URLSearchParams();
  if (filters.dataset) params.set("dataset", filters.dataset);
  if (filters.metric) params.set("metric", filters.metric);
  if (filters.model) params.set("model", filters.model);
  const { data } = await api.get(`/leaderboard?${params.toString()}`);
  return data;
}

export async function getLeaderboardFacets() {
  const { data } = await api.get(`/leaderboard/facets`);
  return data;
}
