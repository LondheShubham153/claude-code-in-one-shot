import { useState } from "react";
import ShortenForm from "./components/ShortenForm";
import ResultCard from "./components/ResultCard";
import type { LinkOut } from "./types";

export default function App() {
  const [result, setResult] = useState<LinkOut | null>(null);

  return (
    <main className="page">
      <header>
        <h1>Shorten a URL</h1>
        <p className="subtitle">
          Reliable. SSRF-blocked. Safe-Browsing-checked. Click counts run on Temporal.
        </p>
      </header>
      {result === null ? (
        <ShortenForm onResult={setResult} />
      ) : (
        <ResultCard result={result} onReset={() => setResult(null)} />
      )}
    </main>
  );
}
