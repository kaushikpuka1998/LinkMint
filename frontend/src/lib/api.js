import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  withCredentials: true,
});

// Links
export const shortenUrl = (payload) => api.post("/shorten", payload);
export const bulkShorten = (urls) => api.post("/shorten/bulk", { urls });
export const getLinks = (params) => api.get("/links", { params });
export const getStats = () => api.get("/stats");
export const getHealth = () => api.get("/health");
export const deleteLink = (code) => api.delete(`/links/${code}`);
export const updateLink = (code, data) => api.patch(`/links/${code}`, data);
export const getLinkAnalytics = (code, days = 30) => api.get(`/links/${code}/analytics`, { params: { days } });
export const resolveCode = (code) => api.get(`/resolve/${code}`);

// Auth
export const registerUser = (data) => api.post("/auth/register", data);
export const loginUser = (data) => api.post("/auth/login", data);
export const exchangeSession = (sessionId) => api.post("/auth/session", { session_id: sessionId });
export const getMe = () => api.get("/auth/me");
export const logoutUser = () => api.post("/auth/logout");

// Helpers
export const shortUrlFor = (code) => `${window.location.origin}/${code}`;
export const qrUrlFor = (code) => `${BACKEND_URL}/api/qr/${code}`;
