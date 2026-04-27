// Tiny base64 JWT encoder/decoder for the demo. NOT cryptographically signed.
// Shape parity only: header.payload.signature
export type Role = "viewer" | "uploader" | "admin";
export type Dept = "hr" | "finance" | "legal" | "general";

export interface JwtPayload {
  sub: string;
  dept: Dept;
  role: Role;
  name: string;
  email: string;
  iat?: number;
}

function b64url(input: string): string {
  return btoa(unescape(encodeURIComponent(input)))
    .replace(/=+$/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function b64urlDecode(input: string): string {
  const pad = input.length % 4 === 0 ? "" : "=".repeat(4 - (input.length % 4));
  const b64 = (input + pad).replace(/-/g, "+").replace(/_/g, "/");
  return decodeURIComponent(escape(atob(b64)));
}

export function encodeJwt(payload: JwtPayload): string {
  const header = { alg: "none", typ: "JWT" };
  const body = { ...payload, iat: Math.floor(Date.now() / 1000) };
  return `${b64url(JSON.stringify(header))}.${b64url(JSON.stringify(body))}.demo`;
}

export function decodeJwt(token: string): JwtPayload | null {
  try {
    const [, payload] = token.split(".");
    return JSON.parse(b64urlDecode(payload)) as JwtPayload;
  } catch {
    return null;
  }
}