#!/usr/bin/env node
// Build-time fetcher for GitHub profile + repos.
// Writes src/data/profile.json and src/data/projects.json.

import { writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const USER = process.env.GITHUB_USER ?? "LondheShubham153";
const TOKEN = process.env.GITHUB_TOKEN;

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(__dirname, "..", "src", "data");

const headers = {
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": `portfolio-fetcher/${USER}`,
  ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
};

async function ghFetch(path) {
  const url = `https://api.github.com${path}`;
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const remaining = res.headers.get("x-ratelimit-remaining");
    const reset = res.headers.get("x-ratelimit-reset");
    const resetIso = reset ? new Date(Number(reset) * 1000).toISOString() : null;
    throw new Error(
      `GitHub API ${res.status} ${res.statusText} on ${path}` +
        (remaining !== null ? ` (ratelimit-remaining=${remaining}` : "") +
        (resetIso ? `, resets at ${resetIso})` : remaining !== null ? ")" : "") +
        (TOKEN ? "" : " — set GITHUB_TOKEN to raise the unauthenticated 60/hr limit."),
    );
  }
  return res.json();
}

async function main() {
  const auth = TOKEN ? "authenticated" : "unauthenticated";
  console.log(`[fetch-github] fetching profile + repos for "${USER}" (${auth})`);

  const profile = await ghFetch(`/users/${USER}`);
  const reposRaw = await ghFetch(`/users/${USER}/repos?per_page=100&sort=updated&type=owner`);

  const projects = reposRaw
    .filter((r) => !r.fork && !r.archived && !r.private)
    .map((r) => ({
      name: r.name,
      description: r.description,
      url: r.html_url,
      language: r.language,
      stars: r.stargazers_count,
      forks: r.forks_count,
      topics: r.topics ?? [],
      updated_at: r.updated_at,
    }))
    .sort((a, b) => b.stars - a.stars || a.name.localeCompare(b.name));

  await mkdir(dataDir, { recursive: true });
  await writeFile(
    resolve(dataDir, "profile.json"),
    JSON.stringify(profile, null, 2) + "\n",
  );
  await writeFile(
    resolve(dataDir, "projects.json"),
    JSON.stringify(projects, null, 2) + "\n",
  );

  console.log(
    `[fetch-github] wrote profile.json (${profile.public_repos} public repos)` +
      ` and projects.json (${projects.length} kept after filter)`,
  );
}

main().catch((err) => {
  console.error(`[fetch-github] FAILED: ${err.message}`);
  process.exit(1);
});
