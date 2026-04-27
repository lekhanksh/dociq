export interface Citation {
  filename: string;
  page: number;
  raw: string;
}

// Matches [filename.ext · Page N]
const CITATION_RE = /\[([^\[\]·]+?\.(?:pdf|docx|txt))\s*·\s*Page\s+(\d+)\]/gi;

export function extractCitations(text: string): Citation[] {
  const out: Citation[] = [];
  const seen = new Set<string>();
  let m: RegExpExecArray | null;
  CITATION_RE.lastIndex = 0;
  while ((m = CITATION_RE.exec(text)) !== null) {
    const raw = m[0];
    if (seen.has(raw)) continue;
    seen.add(raw);
    out.push({ filename: m[1].trim(), page: Number(m[2]), raw });
  }
  return out;
}

export function stripCitations(text: string): string {
  return text.replace(CITATION_RE, "").replace(/[ \t]{2,}/g, " ").trim();
}