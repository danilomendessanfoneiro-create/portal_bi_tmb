import type { LoginResponse, User, UserFormValues, UserListResponse } from "./types";

const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
const TOKEN_KEY = "portal_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  document.cookie = `${TOKEN_KEY}=${token}; path=/; SameSite=Lax; max-age=${60 * 60 * 8}`;
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
      if (Array.isArray(detail)) {
        detail = detail.map((d: { msg?: string }) => d.msg || String(d)).join("; ");
      }
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Erro na requisição");
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export function login(loginName: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ login: loginName, password }),
  });
}

export function fetchMe(): Promise<User> {
  return request<User>("/auth/me");
}

export function listUsers(params: {
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: string;
  include_disabled?: boolean;
}): Promise<UserListResponse> {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  if (params.include_disabled) q.set("include_disabled", "true");
  const qs = q.toString();
  return request<UserListResponse>(`/users${qs ? `?${qs}` : ""}`);
}

export function createUser(values: UserFormValues): Promise<User> {
  return request<User>("/users", {
    method: "POST",
    body: JSON.stringify({
      login: values.login,
      password: values.password,
      profile: values.profile,
      branch: values.branch || null,
      display_name: values.display_name || null,
      name: values.name || null,
      code: values.code || null,
      report_emails: values.profile === "filial" ? values.report_emails || null : null,
      enabled: values.enabled,
    }),
  });
}

export function updateUser(id: number, values: Partial<UserFormValues>): Promise<User> {
  const body: Record<string, unknown> = {};
  if (values.login !== undefined) body.login = values.login;
  if (values.password) body.password = values.password;
  if (values.profile !== undefined) body.profile = values.profile;
  if (values.branch !== undefined) body.branch = values.branch || null;
  if (values.display_name !== undefined) body.display_name = values.display_name || null;
  if (values.name !== undefined) body.name = values.name || null;
  if (values.code !== undefined) body.code = values.code || null;
  if (values.report_emails !== undefined) {
    body.report_emails =
      values.profile === "filial" || values.profile === undefined
        ? values.report_emails || null
        : null;
  }
  if (values.enabled !== undefined) body.enabled = values.enabled;
  return request<User>(`/users/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deactivateUser(id: number): Promise<{ detail: string }> {
  return request<{ detail: string }>(`/users/${id}`, { method: "DELETE" });
}

export function listSmtp(params: {
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: string;
  include_disabled?: boolean;
}): Promise<import("./types").SmtpListResponse> {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  if (params.include_disabled) q.set("include_disabled", "true");
  const qs = q.toString();
  return request(`/settings/smtp${qs ? `?${qs}` : ""}`);
}

export function createSmtp(values: import("./types").SmtpFormValues): Promise<import("./types").SmtpSettings> {
  return request("/settings/smtp", {
    method: "POST",
    body: JSON.stringify({
      name: values.name,
      host: values.host,
      port: Number(values.port),
      username: values.username,
      password: values.password,
      use_tls: values.use_tls,
      sender_email: values.sender_email,
      sender_name: values.sender_name,
      timeout_seconds: values.timeout_seconds ? Number(values.timeout_seconds) : null,
      is_default: values.is_default,
      enabled: values.enabled,
    }),
  });
}

export function updateSmtp(
  id: number,
  values: Partial<import("./types").SmtpFormValues>,
): Promise<import("./types").SmtpSettings> {
  const body: Record<string, unknown> = {};
  if (values.name !== undefined) body.name = values.name;
  if (values.host !== undefined) body.host = values.host;
  if (values.port !== undefined) body.port = Number(values.port);
  if (values.username !== undefined) body.username = values.username;
  if (values.password) body.password = values.password;
  if (values.use_tls !== undefined) body.use_tls = values.use_tls;
  if (values.sender_email !== undefined) body.sender_email = values.sender_email;
  if (values.sender_name !== undefined) body.sender_name = values.sender_name;
  if (values.timeout_seconds !== undefined) {
    body.timeout_seconds = values.timeout_seconds ? Number(values.timeout_seconds) : null;
  }
  if (values.is_default !== undefined) body.is_default = values.is_default;
  if (values.enabled !== undefined) body.enabled = values.enabled;
  return request(`/settings/smtp/${id}`, { method: "PUT", body: JSON.stringify(body) });
}

export function deactivateSmtp(id: number): Promise<{ detail: string }> {
  return request(`/settings/smtp/${id}`, { method: "DELETE" });
}

export function listRecipients(params: {
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: string;
  include_disabled?: boolean;
}): Promise<import("./types").RecipientListResponse> {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  if (params.include_disabled) q.set("include_disabled", "true");
  const qs = q.toString();
  return request(`/settings/recipients${qs ? `?${qs}` : ""}`);
}

export function createRecipient(
  values: import("./types").RecipientFormValues,
): Promise<import("./types").EmailRecipient> {
  return request("/settings/recipients", {
    method: "POST",
    body: JSON.stringify({
      name: values.name,
      email: values.email,
      role_title: values.role_title || null,
      department: values.department || null,
      receive_daily: values.receive_daily,
      receive_weekly: values.receive_weekly,
      receive_monthly: values.receive_monthly,
      enabled: values.enabled,
    }),
  });
}

export function updateRecipient(
  id: number,
  values: Partial<import("./types").RecipientFormValues>,
): Promise<import("./types").EmailRecipient> {
  const body: Record<string, unknown> = {};
  if (values.name !== undefined) body.name = values.name;
  if (values.email !== undefined) body.email = values.email;
  if (values.role_title !== undefined) body.role_title = values.role_title || null;
  if (values.department !== undefined) body.department = values.department || null;
  if (values.receive_daily !== undefined) body.receive_daily = values.receive_daily;
  if (values.receive_weekly !== undefined) body.receive_weekly = values.receive_weekly;
  if (values.receive_monthly !== undefined) body.receive_monthly = values.receive_monthly;
  if (values.enabled !== undefined) body.enabled = values.enabled;
  return request(`/settings/recipients/${id}`, { method: "PUT", body: JSON.stringify(body) });
}

export function deactivateRecipient(id: number): Promise<{ detail: string }> {
  return request(`/settings/recipients/${id}`, { method: "DELETE" });
}

export function biUrlWithToken(): string {
  const base = (import.meta.env.VITE_BI_URL || "/bi").replace(/\/$/, "");
  const token = getToken();
  const params = new URLSearchParams();
  if (token) params.set("token", token);
  const qs = params.toString();
  return qs ? `${base}/?${qs}` : `${base}/`;
}

/** BI embutido no shell React (Opção 1 / futuro Superset). */
export function biEmbedUrl(): string {
  const base = (import.meta.env.VITE_BI_URL || "/bi").replace(/\/$/, "");
  const params = new URLSearchParams({ embed: "true" });
  const token = getToken();
  if (token) params.set("token", token);
  return `${base}/?${params.toString()}`;
}
