import axios from "axios";
import Cookies from "js-cookie";

// Use same-origin API routes so the app works for friends too.
// Next.js rewrites proxy `/api/v1/*` to the backend container.
const API_BASE = "";

export const apiClient = axios.create({
  baseURL: `${API_BASE}/api/v1`.replace(/\/+$/, ""),
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Attach JWT token to every request
apiClient.interceptors.request.use(config => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
apiClient.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = Cookies.get("refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post(`/api/v1/auth/refresh`, { refresh_token: refreshToken });
          Cookies.set("access_token", data.access_token, { secure: true, sameSite: "strict" });
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(original);
        } catch {
          Cookies.remove("access_token");
          Cookies.remove("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) => apiClient.post("/auth/login", { email, password }),
  register: (data: any) => apiClient.post("/auth/register", data),
  me: () => apiClient.get("/auth/me"),
  updateMe: (data: any) => apiClient.put("/auth/me", data),
  logout: (refreshToken: string) => apiClient.post("/auth/logout", { refresh_token: refreshToken }),
};

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatApi = {
  sendMessage: (data: { message: string; session_id?: string | null }) => apiClient.post("/chat/message", data),
  getSessions: () => apiClient.get("/chat/sessions"),
  getSession: (token: string) => apiClient.get(`/chat/sessions/${token}`),
  deleteSession: (token: string) => apiClient.delete(`/chat/sessions/${token}`),
};

// ── Scholarships ──────────────────────────────────────────────────────────────
export const scholarshipApi = {
  list: (params?: any) => apiClient.get("/scholarships/", { params }),
  search: (params: any) => apiClient.get("/scholarships/search", { params }),
  getById: (id: string) => apiClient.get(`/scholarships/${id}`),
  save: (id: string) => apiClient.post(`/scholarships/${id}/save`),
  upcomingDeadlines: (days?: number) => apiClient.get("/scholarships/upcoming/deadlines", { params: { days } }),
};

// ── Admin ──────────────────────────────────────────────────────────────────────
export const adminApi = {
  stats: () => apiClient.get("/admin/stats"),
  createScholarship: (data: any) => apiClient.post("/admin/scholarships", data),
  updateScholarship: (id: string, data: any) => apiClient.put(`/admin/scholarships/${id}`, data),
  deleteScholarship: (id: string) => apiClient.delete(`/admin/scholarships/${id}`),
  uploadPdf: (formData: FormData) => apiClient.post("/admin/upload", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  listUsers: (params?: any) => apiClient.get("/admin/users", { params }),
};

// ── Reminders ─────────────────────────────────────────────────────────────────
export const reminderApi = {
  create: (data: any) => apiClient.post("/reminders/", data),
  list: () => apiClient.get("/reminders/"),
  delete: (id: string) => apiClient.delete(`/reminders/${id}`),
};
