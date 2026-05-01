import { useState } from "react";
import type { LinkOut } from "../types";

interface Props {
  result: LinkOut;
  onReset: () => void;
}

export default function ResultCard({ result, onReset }: Props) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(result.short_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="card">
      <h2>Short URL</h2>
      <a className="short-link" href={result.short_url} target="_blank" rel="noopener">
        {result.short_url}
      </a>
      <div className="row">
        <button type="button" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </button>
        <button type="button" className="secondary" onClick={onReset}>
          Shorten another
        </button>
      </div>
      <dl className="meta">
        <dt>Original</dt>
        <dd className="truncate">{result.url}</dd>
        <dt>Clicks</dt>
        <dd>{result.click_count}</dd>
        <dt>Slug</dt>
        <dd><code>{result.slug}</code></dd>
      </dl>
    </div>
  );
}
