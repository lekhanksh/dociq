# Requirements Document

## Introduction

This document defines the requirements for **DocIQ Secure RAG Chatbot** — a ChatGPT-like document intelligence platform deployed entirely within a company's AWS VPC and private subnets. The system allows employees to upload sensitive company documents and ask natural-language questions, receiving AI-generated answers with source citations. All data processing and storage remains inside the company's private network boundary, with no sensitive data traversing the public internet. The solution is built on the existing Python/FastAPI backend and React/TypeScript frontend, and must operate within a $30 AWS credits budget.

---

## Glossary

- **Chatbot**: The end-to-end DocIQ application that accepts user questions and returns AI-generated answers grounded in company documents.
- **RAG_Pipeline**: The Retrieval-Augmented Generation subsystem that retrieves relevant document chunks and passes them as context to the LLM.
- **VPC**: AWS Virtual Private Cloud — the isolated network boundary within which all compute and data resources reside.
- **Private_Subnet**: A subnet with no direct route to the public internet, used to host backend compute and database resources.
- **Document_Processor**: The backend component responsible for parsing uploaded files, splitting them into chunks, and generating embeddings.
- **Vector_Store**: The storage component (SQLite for dev, pgvector/Aurora for staging/prod) that persists document chunk embeddings and supports similarity search.
- **Embedder**: The component that converts text chunks and user queries into fixed-dimension vector representations for similarity search.
- **Bedrock_Client**: The AWS SDK client that invokes Amazon Bedrock LLM models (Amazon Nova Pro or Claude) for answer generation.
- **S3_Bucket**: The AWS S3 bucket used to store original uploaded documents, accessed via VPC endpoint (no public internet).
- **VPC_Endpoint**: An AWS PrivateLink endpoint that allows private subnet resources to reach AWS services (Bedrock, S3, Secrets Manager) without traversing the public internet.
- **Auth_Service**: The JWT-based authentication and authorisation component.
- **RBAC**: Role-Based Access Control — the permission model with roles: `admin`, `uploader`, `viewer`.
- **Audit_Log**: An append-only log of security-relevant events (logins, uploads, queries, deletions).
- **ALB**: AWS Application Load Balancer — the internal load balancer that routes HTTPS traffic from within the VPC to backend containers.
- **ECS_Task**: An AWS ECS Fargate task running a Docker container for the backend or frontend service.
- **Aurora_Cluster**: An Amazon Aurora PostgreSQL Serverless v2 cluster with the pgvector extension, used as the production vector and relational store.
- **Secrets_Manager**: AWS Secrets Manager, used to store and rotate credentials (JWT secret, DB password, API keys).
- **Company**: A tenant unit representing one organisation; all data is isolated per company.
- **Department**: A sub-unit within a Company used for document access scoping.
- **Chunk**: A fixed-size text segment (≤ 500 characters with 50-character overlap) extracted from a document for embedding and retrieval.
- **Citation**: A reference returned alongside an AI answer that identifies the source document and a text snippet.

---

## Requirements

### Requirement 1: Secure VPC-Only Deployment

**User Story:** As a company IT administrator, I want all chatbot infrastructure deployed inside our AWS VPC with private subnets, so that sensitive company documents never leave our private network boundary.

#### Acceptance Criteria

1. THE Chatbot SHALL deploy all compute resources (backend ECS tasks, database) exclusively in private subnets with no inbound route from the public internet.
2. THE Chatbot SHALL access AWS Bedrock, S3, and Secrets Manager exclusively through VPC endpoints, so that no traffic to these services traverses the public internet.
3. WHEN a VPC endpoint for a required AWS service is unavailable, THE Chatbot SHALL refuse to start and SHALL emit a startup error describing the missing endpoint.
4. THE ALB SHALL be configured as an internal load balancer, accessible only from within the VPC CIDR range.
5. THE Chatbot SHALL enforce TLS 1.2 or higher on all internal service-to-service communication.
6. WHERE a NAT Gateway is required for outbound internet access, THE Chatbot SHALL route only non-sensitive operational traffic (e.g., OS package updates during build) through it, and SHALL NOT route document data or query payloads through it.

---

### Requirement 2: User Authentication and Role-Based Access Control

**User Story:** As a company administrator, I want employees to authenticate with company credentials and be assigned roles, so that access to documents and features is appropriately restricted.

#### Acceptance Criteria

1. WHEN a user submits valid credentials (email, password, company slug), THE Auth_Service SHALL return a signed JWT access token with a 24-hour expiry.
2. WHEN a user submits invalid credentials or an unrecognised company slug, THE Auth_Service SHALL return HTTP 401 and SHALL NOT reveal which field was incorrect.
3. WHILE a JWT token is valid, THE Auth_Service SHALL include the user's role, department, and company identifier in the token payload.
4. WHEN a JWT token has expired, THE Auth_Service SHALL return HTTP 401 and SHALL NOT process the associated request.
5. THE RBAC SHALL enforce three roles: `admin` (full access), `uploader` (upload and query), and `viewer` (query only).
6. WHEN a `viewer` role user attempts to upload a document, THE Auth_Service SHALL return HTTP 403.
7. WHEN an `uploader` role user attempts to access admin endpoints, THE Auth_Service SHALL return HTTP 403.
8. THE Auth_Service SHALL hash all passwords using bcrypt before storage and SHALL NOT store plaintext passwords.
9. WHEN a login attempt is made more than 10 times within 60 seconds from the same email address, THE Auth_Service SHALL return HTTP 429 and SHALL block further attempts for that window.

---

### Requirement 3: Document Upload and Processing

**User Story:** As an uploader, I want to upload PDF, DOCX, and TXT documents tagged with a department, so that the documents are indexed and available for querying by authorised users.

#### Acceptance Criteria

1. WHEN an authorised user uploads a file, THE Document_Processor SHALL accept files of type PDF, DOCX, and TXT up to 10 MB in size.
2. WHEN a file exceeding 10 MB is uploaded, THE Document_Processor SHALL return HTTP 413 with a descriptive error message.
3. WHEN a file of an unsupported type is uploaded, THE Document_Processor SHALL return HTTP 415 with a descriptive error message.
4. WHEN a valid file is uploaded, THE Document_Processor SHALL extract the full text content and split it into Chunks of at most 500 characters with a 50-character overlap.
5. WHEN text extraction from a PDF or DOCX file fails, THE Document_Processor SHALL return HTTP 422 with a descriptive error and SHALL NOT store a partial document.
6. WHEN Chunks are generated, THE Embedder SHALL generate a 384-dimension embedding vector for each Chunk and store the Chunk and its embedding in the Vector_Store.
7. WHEN a document is successfully processed, THE Document_Processor SHALL store the original file in the S3_Bucket under a key scoped to the company identifier, and SHALL record the S3 key in the document metadata.
8. WHEN a document is successfully uploaded and indexed, THE Audit_Log SHALL record the event with the uploader's user ID, company ID, department, filename, and chunk count.
9. THE Document_Processor SHALL associate each Chunk with the uploader's company ID and department to enforce data isolation during retrieval.
10. WHEN an upload request is made more than 20 times within 60 seconds by the same user, THE Document_Processor SHALL return HTTP 429.

---

### Requirement 4: Document Retrieval and RAG Query

**User Story:** As an employee, I want to ask natural-language questions about company documents and receive accurate, cited answers, so that I can quickly find information without manually searching files.

#### Acceptance Criteria

1. WHEN a user submits a question, THE RAG_Pipeline SHALL embed the question using the Embedder and retrieve the top-K most semantically similar Chunks from the Vector_Store, filtered to the user's company ID.
2. WHILE a user has the `viewer` or `uploader` role, THE RAG_Pipeline SHALL restrict Chunk retrieval to the user's assigned department; admin users SHALL retrieve across all departments.
3. WHEN relevant Chunks are found, THE Bedrock_Client SHALL construct a prompt containing the retrieved Chunks as context and SHALL invoke the configured Bedrock model to generate an answer.
4. WHEN no relevant Chunks are found for a question, THE RAG_Pipeline SHALL return a response indicating that no matching documents were found, without invoking the Bedrock_Client.
5. WHEN the Bedrock_Client receives a response, THE RAG_Pipeline SHALL return the answer text together with a list of Citations, each containing the source filename, department, and a text snippet of at most 300 characters.
6. WHEN a query request is made more than 30 times within 60 seconds by the same user, THE RAG_Pipeline SHALL return HTTP 429.
7. WHEN the Bedrock_Client invocation fails due to a service error, THE RAG_Pipeline SHALL return HTTP 503 with a descriptive error and SHALL NOT return a partial or fabricated answer.
8. THE RAG_Pipeline SHALL log each query event to the Audit_Log, including the user ID, company ID, question text, and number of Chunks retrieved.
9. WHEN a question contains aggregation keywords (e.g., "total", "sum", "across all"), THE RAG_Pipeline SHALL retrieve up to 15 Chunks to support multi-document reasoning.

---

### Requirement 5: Document Management

**User Story:** As an admin, I want to list, view, and delete documents in the company's collection, so that I can manage the knowledge base and remove outdated or sensitive content.

#### Acceptance Criteria

1. WHEN an authenticated user requests the document list, THE Chatbot SHALL return only documents belonging to the user's company, filtered by department for non-admin users.
2. WHEN an admin user deletes a document, THE Chatbot SHALL remove all associated Chunks from the Vector_Store and SHALL record the deletion in the Audit_Log.
3. WHEN a non-admin user attempts to delete a document, THE Chatbot SHALL return HTTP 403.
4. THE Chatbot SHALL expose a collection statistics endpoint that returns the total document count, total Chunk count, and per-department document counts for the authenticated user's company.
5. WHEN a document is deleted, THE Chatbot SHALL NOT remove the original file from the S3_Bucket automatically, to preserve an audit trail; S3 lifecycle policies SHALL govern retention.

---

### Requirement 6: ChatGPT-Like Conversational UI

**User Story:** As an employee, I want a chat interface similar to ChatGPT, so that I can ask questions conversationally and see cited answers in a familiar, intuitive layout.

#### Acceptance Criteria

1. THE Chatbot SHALL present a chat interface with a scrollable message history, a text input field, and a send button.
2. WHEN a user submits a question, THE Chatbot SHALL display a typing indicator while the response is being generated.
3. WHEN a response is received, THE Chatbot SHALL render the answer text and display each Citation as a clickable chip showing the source filename.
4. WHEN a Citation chip is clicked, THE Chatbot SHALL display the associated text snippet in a tooltip or expandable panel.
5. THE Chatbot SHALL display suggested starter questions on the empty chat state to guide new users.
6. THE Chatbot SHALL support markdown rendering in AI responses (bold, lists, code blocks).
7. WHEN a user is not authenticated, THE Chatbot SHALL redirect to the login page and SHALL NOT display any document content.
8. THE Chatbot SHALL display the authenticated user's name, role, and department in the navigation header.

---

### Requirement 7: Budget Constraint — Under $30 AWS Credits

**User Story:** As a company stakeholder, I want the solution to run within $30 of AWS credits, so that we can evaluate the system without significant financial commitment.

#### Acceptance Criteria

1. THE Chatbot SHALL use only AWS services available under the AWS Free Tier or at a combined cost of under $30 per month for a low-usage evaluation deployment (up to 50 users, up to 200 queries per day).
2. THE Chatbot SHALL use Amazon Bedrock with the Amazon Nova Pro model (`amazon.nova-pro-v1:0`) as the default LLM, which is available at lower cost than Claude models.
3. WHERE Aurora Serverless v2 is used, THE Chatbot SHALL configure a minimum ACU of 0.5 and a maximum ACU of 2 to limit database costs.
4. THE Chatbot SHALL store document embeddings in SQLite (development) or Aurora pgvector (staging/production) and SHALL NOT require a dedicated vector database service.
5. THE Chatbot SHALL use a single ECS Fargate task for the backend with 0.5 vCPU and 1 GB memory to minimise compute costs.
6. THE Chatbot SHALL use AWS S3 for document storage and SHALL apply a lifecycle policy to transition objects to S3 Intelligent-Tiering after 30 days.
7. THE Chatbot SHALL expose a `/health` endpoint that reports current vector store document count and Bedrock availability, enabling cost monitoring without additional observability services.

---

### Requirement 8: Audit Logging and Security Observability

**User Story:** As a security officer, I want a complete audit trail of all user actions, so that I can investigate incidents and demonstrate compliance.

#### Acceptance Criteria

1. THE Audit_Log SHALL record every login attempt (successful and failed), document upload, document deletion, and RAG query.
2. WHEN an audit event is recorded, THE Audit_Log SHALL include the UTC timestamp, action type, user email, company ID, user role, and action-specific details.
3. THE Audit_Log SHALL be written to a persistent append-only file and SHALL NOT be modifiable by application users.
4. WHERE CloudWatch Logs is available via VPC endpoint, THE Chatbot SHALL stream Audit_Log entries to a CloudWatch Log Group for centralised retention.
5. WHEN an unauthorised access attempt occurs (HTTP 401 or 403 response), THE Audit_Log SHALL record the attempt including the requested endpoint and the source IP address.

---

### Requirement 9: Document Parser Round-Trip Integrity

**User Story:** As a developer, I want document text extraction to be reliable and verifiable, so that the RAG pipeline operates on accurate content.

#### Acceptance Criteria

1. WHEN a PDF file is provided, THE Document_Processor SHALL extract all selectable text from all pages and return a non-empty string for documents containing text.
2. WHEN a DOCX file is provided, THE Document_Processor SHALL extract text from all paragraphs and return a non-empty string for documents containing text.
3. WHEN a TXT or Markdown file is provided, THE Document_Processor SHALL decode the file as UTF-8 and return the full content.
4. FOR ALL valid text documents, chunking then reassembling all Chunks by concatenation SHALL produce a string that contains all tokens present in the original extracted text (round-trip completeness property).
5. WHEN the Document_Processor splits text into Chunks, each consecutive pair of Chunks SHALL share an overlap region of exactly 50 characters, verifiable by comparing the tail of Chunk N with the head of Chunk N+1.

---

### Requirement 10: Multi-Tenancy and Data Isolation

**User Story:** As a company administrator, I want our company's documents and queries to be completely isolated from other companies, so that sensitive data cannot be accessed by other tenants.

#### Acceptance Criteria

1. THE Chatbot SHALL associate every document Chunk with a company ID at ingestion time and SHALL filter all Vector_Store queries by company ID.
2. WHEN a user from Company A submits a query, THE RAG_Pipeline SHALL return only Chunks belonging to Company A, even if Company B has documents with higher semantic similarity to the query.
3. THE Chatbot SHALL associate every user account with exactly one company ID and SHALL enforce this association on every authenticated request.
4. WHEN an admin user of Company A attempts to access documents or users of Company B via API manipulation, THE Chatbot SHALL return HTTP 403.
5. THE Chatbot SHALL store company data in logically separate partitions within the shared database, identified by company ID columns with indexed lookups.
