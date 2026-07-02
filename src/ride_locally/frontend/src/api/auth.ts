import { apiUrl } from "./client";
import { z } from "zod";

const LoginBodySchema = z.object({
  email: z.email().optional(),
  username: z.string().optional(),
  password: z.string(),
}).refine(
  (data) => data.email || data.username,
  { error: "Email or username required" }
)

type LoginBody = z.infer<typeof LoginBodySchema>

export type TokenResponse = {
  token: string;
  expires_at: string;
  token_type: string;
}


export function logout(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("access_token_expires");
}

export async function login(body: LoginBody): Promise<TokenResponse> {
  const parsed = LoginBodySchema.safeParse(body);

  if (!parsed.success) {
    throw new Error(
      parsed.error.issues.map((issue) => issue.message).join(", ")
    );
  }
  const res = await fetch(apiUrl("/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail ?? "Login failed");
  }

  return res.json();
}
