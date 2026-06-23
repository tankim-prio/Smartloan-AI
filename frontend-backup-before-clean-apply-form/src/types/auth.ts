export type UserRole = "admin" | "user";

export type User = {
  id: number;
  full_name: string;
  email: string;
  phone?: string | null;
  role: UserRole;
  is_active: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};
