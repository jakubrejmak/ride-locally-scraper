import { apiUrl } from "./client";

type LoginBody = {
  email?: string;
  username?: string;
  password?: string;
}

type TokenResponse = {
  access_token: string;
  token_type: string;
}


export async function login(body: LoginBody): Promise<TokenResponse> {
  const res = await fetch(apiUrl("/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    throw new Error((await res.json())["detail"])
  }

  return res.json();
}
