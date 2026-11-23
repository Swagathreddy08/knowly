"use client";

import { FormEvent, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type DocumentItem = {
  id: string;
  filename: string;
  status: "uploaded" | "processing" | "indexed" | "failed";
  chunk_count: number;
  error: string | null;
};

type Citation = {
  document_id: string;
  filename: string;
  chunk_index: number;
  excerpt: string;
};

export default function Home() {
  const [token, setToken] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setToken(localStorage.getItem("knowly_token") || "");
  }, []);

  useEffect(() => {
    if (!token) return;
    const load = async () => {
      const response = await fetch(`${API_URL}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) setDocuments(await response.json());
    };
    load();
  }, [token]);

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    const response = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_name: data.get("tenant"),
        email: data.get("email"),
        password: data.get("password"),
      }),
    });
    const body = await response.json();
    if (!response.ok) {
      setError(body.detail || "Registration failed");
      return;
    }
    localStorage.setItem("knowly_token", body.access_token);
    setToken(body.access_token);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    const file = data.get("file") as File;
    if (!file?.size) return;
    setLoading(true);
    const response = await fetch(`${API_URL}/documents`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: data,
    });
    setLoading(false);
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail || "Upload failed");
      return;
    }
    const document = await response.json();
    setDocuments((current) => [document, ...current]);
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const response = await fetch(`${API_URL}/chat/query`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 5 }),
    });
    setLoading(false);
    const body = await response.json();
    if (!response.ok) {
      setError(body.detail || "Question failed");
      return;
    }
    setAnswer(body.answer);
    setCitations(body.citations);
  }

  function logout() {
    localStorage.removeItem("knowly_token");
    setToken("");
  }

  if (!token) {
    return (
      <main className="auth card">
        <h1>Welcome to <span style={{ color: "#4f67d7" }}>Knowly</span></h1>
        <p>Create your workspace to start indexing organizational knowledge.</p>
        <form onSubmit={register}>
          <input name="tenant" placeholder="Workspace name" required minLength={2} />
          <input name="email" type="email" placeholder="Work email" required />
          <input name="password" type="password" placeholder="Password (12+ characters)" required minLength={12} />
          <button type="submit">Create workspace</button>
        </form>
        {error && <p className="error">{error}</p>}
      </main>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">Knowly<span>.</span></div>
        <h2>Knowledge base</h2>
        {documents.map((document) => (
          <div className="document" key={document.id}>
            <div>{document.filename}</div>
            <div className="document-status">
              {document.status} · {document.chunk_count} chunks
            </div>
          </div>
        ))}
      </aside>

      <main className="main">
        <div className="topbar">
          <h1>Research assistant</h1>
          <button type="button" onClick={logout}>Sign out</button>
        </div>

        <section className="card" style={{ marginTop: 24 }}>
          <h2>Upload document</h2>
          <form className="upload-row" onSubmit={upload}>
            <input name="file" type="file" accept=".pdf,.docx,.csv,.txt" required />
            <button type="submit" disabled={loading}>Upload</button>
          </form>
        </section>

        <section className="card" style={{ marginTop: 16 }}>
          <h2>Ask your knowledge base</h2>
          <form className="query-row" onSubmit={ask}>
            <input
              type="text"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a grounded question..."
              minLength={3}
              maxLength={4000}
              required
            />
            <button type="submit" disabled={loading}>Ask</button>
          </form>

          {answer && <div className="answer">{answer}</div>}
          {citations.length > 0 && (
            <div className="citations">
              {citations.map((citation) => (
                <div className="citation" key={`${citation.document_id}-${citation.chunk_index}`}>
                  <strong>{citation.filename} · chunk {citation.chunk_index + 1}</strong>
                  <p>{citation.excerpt}</p>
                </div>
              ))}
            </div>
          )}
          {error && <p className="error">{error}</p>}
        </section>
      </main>
    </div>
  );
}
