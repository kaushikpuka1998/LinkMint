import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const shortenUrl = (payload) => axios.post(`${API}/shorten`, payload);
export const getLinks = () => axios.get(`${API}/links`);
export const getStats = () => axios.get(`${API}/stats`);
export const getHealth = () => axios.get(`${API}/health`);
export const deleteLink = (code) => axios.delete(`${API}/links/${code}`);
export const resolveCode = (code) => axios.get(`${API}/resolve/${code}`);

export const shortUrlFor = (code) => `${window.location.origin}/${code}`;
