const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/+$/, '');

async function request(method, path, data, config = {}) {
  const headers = { ...config.headers };
  let body;

  if (data instanceof FormData) {
    body = data;
    for (const header of Object.keys(headers)) {
      if (header.toLowerCase() === 'content-type') {
        delete headers[header];
      }
    }
  } else if (data !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(data);
  }

  const response = await fetch(`${API_BASE}${path}`, { method, headers, body });
  const responseData = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(responseData?.detail || `Request failed (${response.status})`);
    error.response = { data: responseData, status: response.status };
    throw error;
  }

  return { data: responseData };
}

export const apiClient = {
  get: (path, config) => request('GET', path, undefined, config),
  post: (path, data, config) => request('POST', path, data, config),
  delete: (path, config) => request('DELETE', path, undefined, config),
};