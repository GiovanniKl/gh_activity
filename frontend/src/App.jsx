import { useEffect, useMemo, useState } from "react";
import ActivityGroups from "./components/ActivityGroups";
import Heatmap from "./components/Heatmap";
import Sidebar from "./components/Sidebar";
import { fetchActivity, fetchMeta, fetchOrgs, triggerSync } from "./api";

function isoDaysAgo(days) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function App() {
  const [since, setSince] = useState(isoDaysAgo(364));
  const [until, setUntil] = useState(todayIso());
  const [items, setItems] = useState([]);
  const [orgs, setOrgs] = useState([]);
  const [selectedOrgs, setSelectedOrgs] = useState(new Set());
  const [includePrivate, setIncludePrivate] = useState(true);
  const [includeNonDefault, setIncludeNonDefault] = useState(true);
  const [selectedDay, setSelectedDay] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);

  async function loadAll() {
    setLoading(true);
    try {
      const [activityRes, orgsRes, metaRes] = await Promise.all([
        fetchActivity(since, until),
        fetchOrgs(),
        fetchMeta(),
      ]);
      setItems(activityRes.items);
      setOrgs(orgsRes.orgs);
      setLastSyncedAt(metaRes.last_synced_at);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [since, until]);

  useEffect(() => {
    setSelectedOrgs((prev) => {
      const next = new Set(prev);
      let changed = false;
      for (const o of orgs) {
        if (!next.has(o)) {
          next.add(o);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [orgs]);

  async function handleSync() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await triggerSync();
      if (result.ok) {
        setSyncMessage(
          `Synced ${result.repos_scanned} repos, ${result.items_upserted} new items in ${result.duration_seconds.toFixed(1)}s`
        );
      } else {
        setSyncMessage(`Sync failed: ${result.error}`);
      }
      await loadAll();
    } finally {
      setSyncing(false);
    }
  }

  function toggleOrg(org) {
    setSelectedOrgs((prev) => {
      const next = new Set(prev);
      if (next.has(org)) next.delete(org);
      else next.add(org);
      return next;
    });
  }

  function handleDayClick(day) {
    setSelectedDay((prev) => (prev === day ? null : day));
  }

  const baseFiltered = useMemo(
    () =>
      items.filter(
        (it) =>
          selectedOrgs.has(it.org) &&
          (includePrivate || !it.private) &&
          (includeNonDefault || it.type !== "commit" || it.on_default_branch)
      ),
    [items, selectedOrgs, includePrivate, includeNonDefault]
  );

  const dailyCounts = useMemo(() => {
    const map = new Map();
    for (const it of baseFiltered) {
      const day = it.date.slice(0, 10);
      map.set(day, (map.get(day) || 0) + 1);
    }
    return map;
  }, [baseFiltered]);

  const displayedItems = useMemo(() => {
    if (!selectedDay) return baseFiltered;
    return baseFiltered.filter((it) => it.date.slice(0, 10) === selectedDay);
  }, [baseFiltered, selectedDay]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>GitHub Activity</h1>
        <div className="header-actions">
          <span className="last-sync">
            {lastSyncedAt ? `Last synced ${new Date(lastSyncedAt).toLocaleString()}` : "Never synced"}
          </span>
          <button onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing…" : "Sync now"}
          </button>
        </div>
      </header>
      {syncMessage && <div className="sync-message">{syncMessage}</div>}
      <div className="app-body">
        <Sidebar
          orgs={orgs}
          selectedOrgs={selectedOrgs}
          onToggleOrg={toggleOrg}
          includePrivate={includePrivate}
          onToggleIncludePrivate={() => setIncludePrivate((v) => !v)}
          includeNonDefault={includeNonDefault}
          onToggleIncludeNonDefault={() => setIncludeNonDefault((v) => !v)}
          since={since}
          until={until}
          onChangeSince={setSince}
          onChangeUntil={setUntil}
        />
        <main className="app-main">
          <Heatmap
            dailyCounts={dailyCounts}
            since={since}
            until={until}
            selectedDay={selectedDay}
            onSelectDay={handleDayClick}
          />
          {loading ? (
            <p className="muted">Loading…</p>
          ) : (
            <ActivityGroups
              items={displayedItems}
              selectedDay={selectedDay}
              onClearDay={() => setSelectedDay(null)}
            />
          )}
        </main>
      </div>
    </div>
  );
}
