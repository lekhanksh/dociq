# DocIQ - Interactive System Design Diagrams

## 📊 Available Diagrams

I've created 4 professional AWS architecture diagrams with proper AWS styling and realistic cost breakdowns. Each diagram can be opened directly in your browser.

---

## 1. High-Level Architecture (`diagram_1_architecture.html`)

**What it shows:**
- Complete system architecture from frontend to backend to data layer
- Demo vs Production differences clearly marked
- All AWS services used (ECS, S3, Bedrock, RDS, etc.)
- **Realistic cost breakdown by scale:**
  - Demo/Test: ~$35/month (testing only, ~10 queries/day)
  - Small Team (1-50 users): ~$71/month (~500 queries/day)
  - Medium Company (50-500 users): ~$235/month (~5K queries/day)
  - Enterprise (500-5000 users): ~$1,547/month (~50K queries/day)
- Performance metrics (2-3s query, 5-10s upload, 99.9% uptime)

**Features:**
- Color-coded components (Frontend, Backend, Database, Storage, AI)
- Animated arrows showing data flow
- Service boxes with descriptions
- Legend explaining each layer
- Responsive design

**Open it:**
```bash
open diagram_1_architecture.html
```

---

## 2. VPC Architecture with Endpoints (`diagram_2_vpc_architecture.html`)

**What it shows:**
- Complete VPC setup with 2 availability zones (us-east-1a, us-east-1b)
- Public subnets (ALB) and Private subnets (ECS, RDS)
- All 5 VPC endpoints (S3, Bedrock, Secrets Manager, ECR, CloudWatch)
- Security groups with inbound/outbound rules
- Multi-AZ deployment for high availability

**Features:**
- Color-coded subnets (green = public, red = private)
- VPC endpoint cards with cost breakdown
- Security group rules clearly displayed
- Hover effects on all components
- Shows why we use VPC endpoints (no internet exposure)

**Open it:**
```bash
open diagram_2_vpc_architecture.html
```

---

## 3. Document Upload Flow (`diagram_3_upload_flow.html`)

**What it shows:**
- Complete 9-step upload pipeline from browser to S3
- Each step with detailed explanation
- Code examples showing actual implementation
- Validation steps (file type, size, role)
- Text extraction, chunking, embedding generation
- Database storage and S3 upload

**Features:**
- Step-by-step flow with numbered circles
- Animated slide-in effects
- Code blocks showing actual data
- Time badge showing total time (5-10 seconds)
- Hover effects on each step
- Clear icons for each stage

**Open it:**
```bash
open diagram_3_upload_flow.html
```

---

## 4. Query Flow / RAG Pipeline (`diagram_4_query_flow.html`)

**What it shows:**
- Complete 11-step RAG pipeline from question to answer
- Query complexity detection (simple vs complex)
- Vector similarity search with pgvector
- Multi-tenant filtering (company_id + department)
- Context building for multiple documents
- AWS Bedrock API call with system prompt
- Answer generation with citations
- Audit logging

**Features:**
- Step-by-step flow with numbered circles
- Animated slide-in effects
- Code blocks showing SQL queries and API calls
- Highlighted keywords (total, calculate, sum, all, across)
- Time badge showing total time (2-3 seconds)
- Purple color scheme (different from upload flow)

**Open it:**
```bash
open diagram_4_query_flow.html
```

---

## 🎨 Design Features

All diagrams include:

✅ **Interactive hover effects** - Components scale and highlight on hover
✅ **Smooth animations** - Fade-in, slide-in, bounce effects
✅ **AWS-style colors** - Orange (#FF9900) for AWS, purple for services
✅ **Tooltips** - Additional information on hover
✅ **Code blocks** - Actual code examples with syntax highlighting
✅ **Responsive design** - Works on desktop and tablet
✅ **Print-friendly** - Can be saved as PDF (Cmd+P)
✅ **No external dependencies** - Pure HTML/CSS/JS, works offline

---

## 📸 How to Use in Presentation

### Option 1: Open in Browser
```bash
# Open all diagrams in separate tabs
open diagram_1_architecture.html
open diagram_2_vpc_architecture.html
open diagram_3_upload_flow.html
open diagram_4_query_flow.html
```

Then switch between tabs during your presentation.

### Option 2: Save as PDF
1. Open each HTML file in browser
2. Press `Cmd + P` (Mac) or `Ctrl + P` (Windows)
3. Select "Save as PDF"
4. Now you have PDF versions to include in slides

### Option 3: Take Screenshots
1. Open HTML file in browser
2. Zoom to 100% or 125% for better visibility
3. Use screenshot tool (Cmd + Shift + 4 on Mac)
4. Capture the diagram
5. Insert into PowerPoint/Keynote

---

## 🎤 When to Show Each Diagram

### During Problem Framing (2 min)
- No diagrams needed, just talk

### During Live Demo (2 min)
- Show the actual app at http://localhost:8080
- No diagrams needed

### During System Design (3.5 min)

**Minute 1:** Show `diagram_1_architecture.html`
- "Here's the high-level architecture..."
- Point out frontend, backend, data layer
- Highlight demo vs production differences

**Minute 2:** Show `diagram_2_vpc_architecture.html`
- "Now let me show you the VPC setup..."
- Point out private subnets, VPC endpoints
- Explain why no internet access

**Minute 3:** Show `diagram_3_upload_flow.html`
- "When you saw me upload that PDF, here's what happened..."
- Walk through steps 1-9 quickly
- Point out validation and chunking

**Minute 3.5:** Show `diagram_4_query_flow.html`
- "And when I asked the question, here's the RAG pipeline..."
- Walk through steps 1-11 quickly
- Point out vector search and Bedrock call

### During Tradeoffs (2 min)
- Keep `diagram_1_architecture.html` visible
- Reference it when talking about decisions

### During Failure Modes (1 min)
- Keep `diagram_1_architecture.html` visible
- Point to components as you discuss failures

---

## 💡 Pro Tips

1. **Practice switching between diagrams** - Know which tab is which
2. **Zoom browser to 125%** - Better visibility for audience
3. **Close unnecessary tabs** - Avoid confusion
4. **Use full screen mode** - Press F11 for distraction-free view
5. **Have backup screenshots** - In case browser crashes
6. **Test on presentation laptop** - Ensure colors look good on projector
7. **Bring USB with HTML files** - In case you need to switch computers

---

## 🎯 Quick Reference

| Diagram | File | Use Case | Duration |
|---------|------|----------|----------|
| Architecture | `diagram_1_architecture.html` | System overview | 1 min |
| VPC | `diagram_2_vpc_architecture.html` | Network security | 30 sec |
| Upload Flow | `diagram_3_upload_flow.html` | Document processing | 30 sec |
| Query Flow | `diagram_4_query_flow.html` | RAG pipeline | 1 min |

---

## 🚀 You're Ready!

All diagrams are production-ready and look professional. They clearly show:
- ✅ What you built (demo)
- ✅ What production should look like
- ✅ How data flows through the system
- ✅ Why you made certain decisions
- ✅ How the system handles failures

Good luck with your presentation! 🎉
