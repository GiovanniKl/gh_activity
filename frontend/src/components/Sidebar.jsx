const PRESETS = [
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "180d", days: 180 },
  { label: "365d", days: 365 },
];

function isoDaysAgo(days) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function Sidebar({
  orgs,
  selectedOrgs,
  onToggleOrg,
  includePrivate,
  onToggleIncludePrivate,
  since,
  until,
  onChangeSince,
  onChangeUntil,
}) {
  return (
    <aside className="sidebar">
      <section className="sidebar-section">
        <h3>Date range</h3>
        <div className="date-presets">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => {
                onChangeSince(isoDaysAgo(p.days - 1));
                onChangeUntil(todayIso());
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
        <label className="date-field">
          Since
          <input type="date" value={since} onChange={(e) => onChangeSince(e.target.value)} />
        </label>
        <label className="date-field">
          Until
          <input type="date" value={until} onChange={(e) => onChangeUntil(e.target.value)} />
        </label>
      </section>

      <section className="sidebar-section">
        <label className="toggle-field">
          <input type="checkbox" checked={includePrivate} onChange={onToggleIncludePrivate} />
          Include private repos
        </label>
      </section>

      <section className="sidebar-section">
        <h3>Organizations</h3>
        {orgs.length === 0 && <p className="muted">No repos synced yet</p>}
        <ul className="org-list">
          {orgs.map((org) => (
            <li key={org}>
              <label className="toggle-field">
                <input
                  type="checkbox"
                  checked={selectedOrgs.has(org)}
                  onChange={() => onToggleOrg(org)}
                />
                {org}
              </label>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
