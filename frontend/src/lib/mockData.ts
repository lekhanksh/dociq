import type { Dept } from "./jwt";

export interface DocItem {
  id: string;
  filename: string;
  dept: Dept;
  uploadedBy: string;
  uploadedAt: string; // ISO
  chunks: number;
  status: "active";
}

export const mockDocs: DocItem[] = [
  {
    id: "d1",
    filename: "Q3_Financial_Report_2025.pdf",
    dept: "finance",
    uploadedBy: "Sarah Chen",
    uploadedAt: new Date(Date.now() - 2 * 86400_000).toISOString(),
    chunks: 847,
    status: "active",
  },
  {
    id: "d2",
    filename: "Budget_Planning_Template.docx",
    dept: "finance",
    uploadedBy: "Sarah Chen",
    uploadedAt: new Date(Date.now() - 5 * 86400_000).toISOString(),
    chunks: 234,
    status: "active",
  },
  {
    id: "d3",
    filename: "Investment_Policy_v3.pdf",
    dept: "finance",
    uploadedBy: "Marcus Lee",
    uploadedAt: new Date(Date.now() - 7 * 86400_000).toISOString(),
    chunks: 412,
    status: "active",
  },
  {
    id: "d4",
    filename: "Employee_Handbook_2025.pdf",
    dept: "hr",
    uploadedBy: "Alex Roy",
    uploadedAt: new Date(Date.now() - 3 * 86400_000).toISOString(),
    chunks: 312,
    status: "active",
  },
  {
    id: "d5",
    filename: "Master_Services_Agreement.pdf",
    dept: "legal",
    uploadedBy: "Priya Mehta",
    uploadedAt: new Date(Date.now() - 10 * 86400_000).toISOString(),
    chunks: 528,
    status: "active",
  },
  {
    id: "d6",
    filename: "Company_Wiki.txt",
    dept: "general",
    uploadedBy: "Priya Mehta",
    uploadedAt: new Date(Date.now() - 14 * 86400_000).toISOString(),
    chunks: 196,
    status: "active",
  },
];

export const mockCollections = { hr: 312, finance: 1493, legal: 528, general: 196 };

export interface Activity {
  id: string;
  user: string;
  action: "Uploaded" | "Queried" | "Deleted";
  dept: Dept;
  document: string;
  timestamp: string;
}

export const mockActivity: Activity[] = [
  { id: "a1", user: "Sarah Chen", action: "Queried", dept: "finance", document: "Q3_Financial_Report_2025.pdf", timestamp: new Date(Date.now() - 2 * 3600_000).toISOString() },
  { id: "a2", user: "Alex Roy", action: "Uploaded", dept: "hr", document: "Employee_Handbook_2025.pdf", timestamp: new Date(Date.now() - 5 * 3600_000).toISOString() },
  { id: "a3", user: "Priya Mehta", action: "Uploaded", dept: "legal", document: "Master_Services_Agreement.pdf", timestamp: new Date(Date.now() - 8 * 3600_000).toISOString() },
  { id: "a4", user: "Marcus Lee", action: "Queried", dept: "finance", document: "Investment_Policy_v3.pdf", timestamp: new Date(Date.now() - 12 * 3600_000).toISOString() },
  { id: "a5", user: "Sarah Chen", action: "Uploaded", dept: "finance", document: "Budget_Planning_Template.docx", timestamp: new Date(Date.now() - 26 * 3600_000).toISOString() },
  { id: "a6", user: "Alex Roy", action: "Queried", dept: "hr", document: "Employee_Handbook_2025.pdf", timestamp: new Date(Date.now() - 30 * 3600_000).toISOString() },
  { id: "a7", user: "Priya Mehta", action: "Deleted", dept: "general", document: "Outdated_Wiki.txt", timestamp: new Date(Date.now() - 36 * 3600_000).toISOString() },
  { id: "a8", user: "Sarah Chen", action: "Queried", dept: "finance", document: "Q3_Financial_Report_2025.pdf", timestamp: new Date(Date.now() - 40 * 3600_000).toISOString() },
  { id: "a9", user: "Marcus Lee", action: "Uploaded", dept: "finance", document: "Investment_Policy_v3.pdf", timestamp: new Date(Date.now() - 48 * 3600_000).toISOString() },
  { id: "a10", user: "Alex Roy", action: "Queried", dept: "hr", document: "Employee_Handbook_2025.pdf", timestamp: new Date(Date.now() - 60 * 3600_000).toISOString() },
  { id: "a11", user: "Priya Mehta", action: "Queried", dept: "legal", document: "Master_Services_Agreement.pdf", timestamp: new Date(Date.now() - 72 * 3600_000).toISOString() },
  { id: "a12", user: "Sarah Chen", action: "Queried", dept: "finance", document: "Budget_Planning_Template.docx", timestamp: new Date(Date.now() - 84 * 3600_000).toISOString() },
  { id: "a13", user: "Marcus Lee", action: "Queried", dept: "finance", document: "Q3_Financial_Report_2025.pdf", timestamp: new Date(Date.now() - 96 * 3600_000).toISOString() },
  { id: "a14", user: "Alex Roy", action: "Uploaded", dept: "hr", document: "Benefits_Guide.pdf", timestamp: new Date(Date.now() - 108 * 3600_000).toISOString() },
  { id: "a15", user: "Priya Mehta", action: "Uploaded", dept: "general", document: "Company_Wiki.txt", timestamp: new Date(Date.now() - 120 * 3600_000).toISOString() },
  { id: "a16", user: "Sarah Chen", action: "Deleted", dept: "finance", document: "Old_Q2_Report.pdf", timestamp: new Date(Date.now() - 132 * 3600_000).toISOString() },
  { id: "a17", user: "Marcus Lee", action: "Queried", dept: "finance", document: "Investment_Policy_v3.pdf", timestamp: new Date(Date.now() - 144 * 3600_000).toISOString() },
  { id: "a18", user: "Alex Roy", action: "Queried", dept: "hr", document: "Benefits_Guide.pdf", timestamp: new Date(Date.now() - 156 * 3600_000).toISOString() },
  { id: "a19", user: "Priya Mehta", action: "Queried", dept: "legal", document: "Master_Services_Agreement.pdf", timestamp: new Date(Date.now() - 168 * 3600_000).toISOString() },
  { id: "a20", user: "Sarah Chen", action: "Uploaded", dept: "finance", document: "Q3_Financial_Report_2025.pdf", timestamp: new Date(Date.now() - 180 * 3600_000).toISOString() },
];

export interface SeededMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sourcesUsed?: number;
}

export const seededFinanceChat: SeededMessage[] = [
  { id: "m1", role: "user", content: "What was our Q3 operating expense?" },
  {
    id: "m2",
    role: "assistant",
    content:
      "The **Q3 operating expense** was **$4.2M**, representing a **12% increase** from Q2. The largest contributors were:\n\n- **Personnel costs**: $2.1M\n- **Infrastructure**: $890K\n- **Marketing & sales**: $640K\n\nThis aligns with the planned hiring ramp documented in the budget template. [Q3_Financial_Report_2025.pdf · Page 4] [Budget_Planning_Template.docx · Page 2]",
    sourcesUsed: 2,
  },
];

export const MOCK_ANSWERS: Record<string, string> = {
  default:
    "Based on the documents in your collection, here's a synthesized answer:\n\n- The relevant policy was last updated this quarter\n- Key thresholds remain unchanged from the prior version\n- Approval flows above $50K still require executive sign-off\n\nLet me know if you'd like me to dig deeper into any specific section. [Q3_Financial_Report_2025.pdf · Page 7] [Investment_Policy_v3.pdf · Page 3]",
  contracts:
    "Across your active contracts, the **key terms** are:\n\n- **Payment net 30** with 1.5% monthly late fee\n- **Termination for convenience** with 60-day notice\n- **Mutual NDAs** covering 3 years post-termination\n- **Limitation of liability** capped at fees paid in trailing 12 months\n\n[Master_Services_Agreement.pdf · Page 2] [Investment_Policy_v3.pdf · Page 5]",
  hr:
    "The latest HR policy changes include:\n\n- **Hybrid policy**: minimum 2 in-office days per week\n- **Parental leave**: extended to 16 weeks fully paid\n- **Wellness stipend**: $1,200 annual reimbursement\n\nAll changes effective this quarter. [Employee_Handbook_2025.pdf · Page 12] [Employee_Handbook_2025.pdf · Page 18]",
  financials:
    "Last quarter's **financial highlights**:\n\n- **Revenue**: $18.4M, up 14% YoY\n- **Gross margin**: 71%, up 2 pts\n- **Operating expense**: $4.2M (+12% QoQ)\n- **Net income**: $3.1M\n\n[Q3_Financial_Report_2025.pdf · Page 1] [Q3_Financial_Report_2025.pdf · Page 4]",
};

export function pickMockAnswer(question: string): string {
  const q = question.toLowerCase();
  if (q.includes("contract") || q.includes("term")) return MOCK_ANSWERS.contracts;
  if (q.includes("hr") || q.includes("policy") || q.includes("policies")) return MOCK_ANSWERS.hr;
  if (q.includes("financial") || q.includes("revenue") || q.includes("quarter")) return MOCK_ANSWERS.financials;
  return MOCK_ANSWERS.default;
}