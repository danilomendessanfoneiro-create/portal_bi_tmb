export type UserProfile = "admin" | "filial";

export interface User {
  id: number;
  login: string;
  profile: UserProfile | string;
  branch?: string | null;
  display_name?: string | null;
  name?: string | null;
  code?: string | null;
  report_emails?: string | null;
  login_email?: string | null;
  must_change_password?: boolean;
  enabled: boolean;
  created_on?: string | null;
  modified_on?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserFormValues {
  login: string;
  password: string;
  profile: string;
  branch: string;
  display_name: string;
  name: string;
  code: string;
  report_emails: string;
  login_email: string;
  enabled: boolean;
  send_provisional?: boolean;
}

export interface SmtpSettings {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
  use_tls: boolean;
  sender_email: string;
  sender_name: string;
  timeout_seconds?: number | null;
  is_default: boolean;
  enabled: boolean;
  created_on?: string | null;
  modified_on?: string | null;
}

export interface SmtpFormValues {
  name: string;
  host: string;
  port: number;
  username: string;
  password: string;
  use_tls: boolean;
  sender_email: string;
  sender_name: string;
  timeout_seconds: string;
  is_default: boolean;
  enabled: boolean;
}

export interface SmtpListResponse {
  items: SmtpSettings[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmailRecipient {
  id: number;
  name: string;
  email: string;
  role_title?: string | null;
  department?: string | null;
  receive_daily: boolean;
  receive_weekly: boolean;
  receive_monthly: boolean;
  enabled: boolean;
  created_on?: string | null;
  modified_on?: string | null;
}

export interface RecipientFormValues {
  name: string;
  email: string;
  role_title: string;
  department: string;
  receive_daily: boolean;
  receive_weekly: boolean;
  receive_monthly: boolean;
  enabled: boolean;
}

export interface RecipientListResponse {
  items: EmailRecipient[];
  total: number;
  page: number;
  page_size: number;
}

export interface Client {
  id: number;
  name: string;
  cnpj: string;
  emails?: string | null;
  enabled: boolean;
  created_on?: string | null;
  modified_on?: string | null;
}

export interface ClientFormValues {
  name: string;
  cnpj: string;
  emails: string;
  enabled: boolean;
}

export interface ClientListResponse {
  items: Client[];
  total: number;
  page: number;
  page_size: number;
}
