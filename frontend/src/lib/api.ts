import { mockCollections, pickMockAnswer } from "./mockData";

// Dynamic API URL based on environment
const getBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  const mode = import.meta.env.MODE;
  switch (mode) {
    case 'demo':
      return 'https://YOUR_EC2_PUBLIC_IP'; // Update after deployment
    case 'staging':
      return 'https://staging.your-domain.com';
    case 'production':
      return 'https://api.your-domain.com';
    default:
      return 'http://localhost:8000';
  }
};

const BASE_URL: string = getBaseUrl();

export interface UploadResponse {
  message: string;
  chunks_indexed: number;
  dept: string;
}

export interface CollectionsInfo {
  hr: number;
  finance: number;
  legal: number;
  general: number;
}

export interface Document {
  id: string;
  filename: string;
  department: string;
  s3_url: string;
  chunks: number;
  uploaded_at: string;
  status: string;
}

export interface DocumentsResponse {
  documents: Document[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export const API_AVAILABLE = BASE_URL.length > 0;

/* ---------- /health ---------- */
export async function getHealth(): Promise<HealthResponse> {
  if (!API_AVAILABLE) {
    return { status: "ok", service: "dociq", version: "1.0.0" };
  }
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("health failed");
  return (await res.json()) as HealthResponse;
}

/* ---------- /collections/info ---------- */
export async function getCollectionsInfo(token: string): Promise<CollectionsInfo> {
  if (!API_AVAILABLE) {
    await new Promise((r) => setTimeout(r, 250));
    return mockCollections;
  }
  const res = await fetch(`${BASE_URL}/collections/info`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("collections failed");
  return (await res.json()) as CollectionsInfo;
}

/* ---------- /documents ---------- */
export async function getDocuments(token: string): Promise<DocumentsResponse> {
  const res = await fetch(`${BASE_URL}/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("documents failed");
  return (await res.json()) as DocumentsResponse;
}

/* ---------- /upload (XHR for progress) ---------- */
export function uploadFile(
  file: File,
  token: string,
  onProgress?: (pct: number) => void,
  department?: string,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    if (!API_AVAILABLE) {
      // Simulated progress
      let pct = 0;
      const tick = setInterval(() => {
        pct = Math.min(100, pct + 8 + Math.random() * 12);
        onProgress?.(pct);
        if (pct >= 100) {
          clearInterval(tick);
          setTimeout(() => {
            resolve({
              message: "indexed",
              chunks_indexed: Math.floor(50 + Math.random() * 400),
              dept: "finance",
            });
          }, 250);
        }
      }, 180);
      return;
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE_URL}/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    // Do NOT set Content-Type — browser sets multipart boundary.
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as UploadResponse);
        } catch {
          reject(new Error("invalid upload response"));
        }
      } else {
        reject(new Error(`upload failed: ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("network error"));
    const form = new FormData();
    form.append("file", file);
    form.append("department", department || "finance"); // Use provided department or default
    xhr.send(form);
  });
}

/* ---------- /query (JSON response) ---------- */
export interface QueryResult {
  answer: string;
  sources: Array<{
    filename: string;
    department: string;
    s3_url: string;
    snippet: string;
    similarity?: number;
  }>;
}

export async function streamQuery(
  question: string,
  token: string,
  onToken: (chunk: string) => void,
  signal?: AbortSignal,
  onComplete?: (result: QueryResult) => void,
): Promise<void> {
  if (!API_AVAILABLE) {
    return typewriter(pickMockAnswer(question), onToken, signal);
  }
  try {
    const res = await fetch(`${BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question }),
      signal,
    });
    if (!res.ok) throw new Error(`query failed: ${res.status}`);
    
    const data: QueryResult = await res.json();
    
    // Simulate streaming for UI effect
    const fullAnswer = data.answer;
    const STEP = 20;
    const INTERVAL = 15;
    return new Promise((resolve) => {
      let i = 0;
      const id = setInterval(() => {
        if (signal?.aborted) {
          clearInterval(id);
          resolve();
          return;
        }
        const next = fullAnswer.slice(i, i + STEP);
        onToken(next);
        i += STEP;
        if (i >= fullAnswer.length) {
          clearInterval(id);
          onComplete?.(data);
          resolve();
        }
      }, INTERVAL);
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    return typewriter(pickMockAnswer(question), onToken, signal);
  }
}

function typewriter(
  full: string,
  onToken: (chunk: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve) => {
    let i = 0;
    const STEP = 30;
    const INTERVAL = 30;
    const id = setInterval(() => {
      if (signal?.aborted) {
        clearInterval(id);
        resolve();
        return;
      }
      const next = full.slice(i, i + STEP);
      onToken(next);
      i += STEP;
      if (i >= full.length) {
        clearInterval(id);
        resolve();
      }
    }, INTERVAL);
  });
}