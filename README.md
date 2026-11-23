"# Knowly

## Enterprise AI Knowledge and Research Assistant

Knowly is an AI-powered knowledge management platform that helps employees find accurate information across organizational documents. Users can upload documents and ask questions in natural language instead of relying on keyword-based search.

## Overview

Organizations often store large amounts of information in documents that are distributed across teams and formats. Finding relevant answers from that knowledge is usually slow and difficult, while traditional keyword search does not always understand the user's intent.

Knowly addresses this problem by combining document processing, semantic and keyword retrieval, reranking, and generative AI. It provides source-grounded responses so users can trace answers back to the documents that support them.

## System Architecture

The application is divided into frontend, backend, AI processing, and data storage layers.

- **Frontend:** Next.js
- **Backend:** Python and FastAPI
- **AI orchestration:** LangChain
- **Structured data and metadata:** PostgreSQL
- **Semantic search:** Pinecone
- **Keyword search:** Elasticsearch
- **Background processing and caching:** Redis
- **Asynchronous task processing:** Celery

Each technology is responsible for a specific part of the platform rather than forcing a single database or service to handle every workload.

## Document Processing Pipeline

Knowly supports PDF, DOCX, and CSV document uploads.

1. Apache Tika extracts text and content from uploaded files.
2. Documents are split into chunks of approximately 512 tokens.
3. Chunking keeps content within model context limits and makes individual sections easier to retrieve.
4. Celery processes documents asynchronously in the background.
5. Redis coordinates the background processing and caching infrastructure.

The pipeline achieved approximately **99.5% task success**.

## Advanced RAG Implementation

Knowly uses a hybrid Retrieval-Augmented Generation (RAG) workflow:

1. The backend receives a user's natural-language question.
2. The query is searched using:
   - **BM25 keyword retrieval** through Elasticsearch
   - **Semantic similarity search** through Pinecone embeddings
3. Results from both retrieval methods are combined.
4. Cohere reranking orders the candidate passages by relevance to the original query.
5. LangChain passes the most relevant context to the language model.
6. The model generates an answer grounded in the retrieved documents.
7. Source citations identify the documents that support the generated answer.

Hybrid retrieval improves results for both natural-language queries and questions containing exact technical terms or identifiers. Citations also help users verify AI-generated responses.

## Security and Multi-Tenancy

Knowly is designed for isolated access across organizations and teams.

- Every user belongs to an authorized tenant.
- Role-Based Access Control (RBAC) controls user permissions.
- Tenant authorization is enforced in document access and retrieval workflows.
- Retrieved context is restricted to data belonging to the user's tenant.

Tenant isolation is implemented as a core architectural requirement instead of relying only on frontend authorization checks.

## Deployment and DevOps

The platform is deployed using:

- AWS EC2
- Docker containers
- Nginx reverse proxy
- GitHub Actions CI/CD

This setup automates application updates and standardizes deployment. The production environment achieved approximately **99.9% uptime**.

## Engineering Challenges

### Relevant retrieval from large documents

Vector-only retrieval does not always perform well for exact technical terms or identifiers. Knowly combines BM25 keyword retrieval with vector similarity and applies Cohere reranking to improve result quality.

### Non-blocking document processing

Text extraction and indexing can take longer than an API request should allow. Celery and Redis move these operations into asynchronous background tasks.

### Secure information boundaries

Enterprise knowledge requires strong tenant isolation. Knowly validates tenant permissions throughout document access and retrieval rather than applying isolation only at the frontend."
