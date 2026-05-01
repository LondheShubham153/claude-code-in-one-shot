import type { LinkOut, ShortenRequest } from "./types";

export async function shorten(url: string): Promise<LinkOut> {
  const body: ShortenRequest = { url };
  const resp = await fetch("/api/links", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      if (typeof err.detail === "string") {
        detail = err.detail;
      } else if (Array.isArray(err.detail)) {
        detail = err.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join("; ");
      }
    } catch {
      /* fall through */
    }
    throw new Error(detail);
  }
  return resp.json();
}

export async function lookup(slug: string): Promise<LinkOut> {
  const resp = await fetch(`/api/links/${encodeURIComponent(slug)}`);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return resp.json();
}
