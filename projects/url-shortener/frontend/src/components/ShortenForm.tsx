import { useState, type FormEvent } from "react";
import { shorten } from "../api";
import type { LinkOut } from "../types";

interface Props {
  onResult: (link: LinkOut) => void;
}

export default function ShortenForm({ onResult }: Props) {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await shorten(url);
      onResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card">
      <label htmlFor="url-input">Paste a URL</label>
      <input
        id="url-input"
        type="url"
        required
        placeholder="https://example.com/some/long/path"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        disabled={submitting}
      />
      <button type="submit" disabled={submitting || !url}>
        {submitting ? "Shortening…" : "Shorten"}
      </button>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}
