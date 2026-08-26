import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Simple helper used by the Dashboard/health checks in Phase 1.
export async function checkHealth() {
  const { data } = await api.get("/health");
  return data;
}
