import { useState } from "react";

const TYPE_LABELS = {
  commit: "Commit",
  pr: "PR",
  issue: "Issue",
  review: "Review",
};

function groupByOrgAndRepo(items) {
  const orgs = new Map();
  for (const item of items) {
    if (!orgs.has(item.org)) orgs.set(item.org, new Map());
    const repos = orgs.get(item.org);
    if (!repos.has(item.repo_full_name)) repos.set(item.repo_full_name, []);
    repos.get(item.repo_full_name).push(item);
  }
  return orgs;
}

function repoKey(org, repoFullName) {
  return `${org}::${repoFullName}`;
}

export default function ActivityGroups({ items, selectedDay, onClearDay }) {
  const [collapsed, setCollapsed] = useState(() => new Set());

  if (items.length === 0) {
    return <p className="muted">No activity in the current filters.</p>;
  }

  const grouped = groupByOrgAndRepo(items);

  function toggleKey(key, isOpenNow) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (isOpenNow) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function expandAll() {
    setCollapsed(new Set());
  }

  function collapseAll() {
    const keys = [];
    for (const [org, repos] of grouped) {
      keys.push(org);
      for (const repoFullName of repos.keys()) keys.push(repoKey(org, repoFullName));
    }
    setCollapsed(new Set(keys));
  }

  return (
    <div className="activity-groups">
      <div className="groups-toolbar">
        <button onClick={expandAll}>Expand all</button>
        <button onClick={collapseAll}>Collapse all</button>
      </div>
      {selectedDay && (
        <div className="day-filter-banner">
          Showing activity for <strong>{selectedDay}</strong> only.{" "}
          <button onClick={onClearDay}>Clear</button>
        </div>
      )}
      {[...grouped.entries()].map(([org, repos]) => {
        const orgCount = [...repos.values()].reduce((n, arr) => n + arr.length, 0);
        return (
          <details
            className="org-group"
            key={org}
            open={!collapsed.has(org)}
            onToggle={(e) => toggleKey(org, e.target.open)}
          >
            <summary>
              {org} <span className="count">({orgCount})</span>
            </summary>
            {[...repos.entries()].map(([repoFullName, repoItems]) => {
              const key = repoKey(org, repoFullName);
              return (
                <details
                  className="repo-group"
                  key={repoFullName}
                  open={!collapsed.has(key)}
                  onToggle={(e) => toggleKey(key, e.target.open)}
                >
                  <summary>
                    {repoFullName} <span className="count">({repoItems.length})</span>
                    {repoItems[0].private && <span className="badge private">private</span>}
                  </summary>
                  <ul className="activity-list">
                    {repoItems.map((item) => (
                      <li key={`${item.type}-${item.sha_or_number}`} className="activity-item">
                        <span className={`badge type-${item.type}`}>{TYPE_LABELS[item.type]}</span>
                        {item.type === "commit" && !item.on_default_branch && (
                          <span className="badge non-default">non-default</span>
                        )}
                        <a href={item.url} target="_blank" rel="noreferrer">
                          {item.title || item.sha_or_number}
                        </a>
                        <span className="activity-date">{item.date.slice(0, 10)}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              );
            })}
          </details>
        );
      })}
    </div>
  );
}
