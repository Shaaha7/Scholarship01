// lib/api-client.ts
import axios from "axios";
import Cookies from "js-cookie";

// Use same-origin API routes so the app works when shared publicly.
const BASE_URL = "";

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`.replace(/\/+$/, ""),
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Request interceptor – attach JWT
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const locale = Cookies.get("locale") || "en";
  config.headers["Accept-Language"] = locale;
  return config;
});

// Response interceptor – auto-refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = Cookies.get("refresh_token");
        if (!refreshToken) throw new Error("No refresh token");
        const res = await axios.post(`/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: newRefresh } = res.data;
        Cookies.set("access_token", access_token, { secure: true, sameSite: "strict" });
        Cookies.set("refresh_token", newRefresh, { secure: true, sameSite: "strict" });
        original.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(original);
      } catch {
        Cookies.remove("access_token");
        Cookies.remove("refresh_token");
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);
