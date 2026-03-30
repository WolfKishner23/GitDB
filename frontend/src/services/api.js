import axios from 'axios';

const API_BASE = 'http://localhost:5000';

export const fetchCommits = () => axios.get(`${API_BASE}/commits`).then(res => res.data);
export const fetchCommit = (h) => axios.get(`${API_BASE}/commits/${h}`).then(res => res.data);
export const fetchDiff = (h1, h2) => axios.get(`${API_BASE}/diff/${h1}/${h2}`).then(res => res.data);
export const checkoutCommit = (h) => axios.post(`${API_BASE}/checkout/${h}`).then(res => res.data);
