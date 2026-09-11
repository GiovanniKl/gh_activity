export async function fetchActivity(since, until) {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (until) params.set("until", until);
  const res = await fetch(`/api/activity?${params}`);
  if (!res.ok) throw new Error("Failed to fetch activity");
  return res.json();
}

export async function fetchOrgs() {
  const res = await fetch("/api/orgs");
  if (!res.ok) throw new Error("Failed to fetch orgs");
  return res.json();
}

export async function fetchMeta() {
  const res = await fetch("/api/meta");
  if (!res.ok) throw new Error("Failed to fetch meta");
  return res.json();
}

export async function triggerSync() {
  const res = await fetch("/api/sync", { method: "POST" });
  if (!res.ok) throw new Error("Sync request failed");
  return res.json();
}
