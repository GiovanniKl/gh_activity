const MONTH_LABELS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function toDateOnly(d) {
  return d.toISOString().slice(0, 10);
}

function buildWeeks(sinceStr, untilStr) {
  const since = new Date(`${sinceStr}T00:00:00Z`);
  const until = new Date(`${untilStr}T00:00:00Z`);
  const start = new Date(since);
  start.setUTCDate(start.getUTCDate() - start.getUTCDay());

  const weeks = [];
  let cur = new Date(start);
  while (cur <= until) {
    const week = [];
    for (let i = 0; i < 7; i++) {
      const inRange = cur >= since && cur <= until;
      week.push(inRange ? toDateOnly(cur) : null);
      cur.setUTCDate(cur.getUTCDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}

function computeThresholds(dailyCounts) {
  const nonZero = [...dailyCounts.values()].filter((c) => c > 0).sort((a, b) => a - b);
  if (!nonZero.length) return [1, 2, 3];
  const q = (p) => nonZero[Math.min(nonZero.length - 1, Math.floor(p * nonZero.length))];
  const t1 = q(0.25) || 1;
  const t2 = Math.max(q(0.5), t1 + 1);
  const t3 = Math.max(q(0.75), t2 + 1);
  return [t1, t2, t3];
}

function levelFor(count, thresholds) {
  if (!count) return 0;
  if (count <= thresholds[0]) return 1;
  if (count <= thresholds[1]) return 2;
  if (count <= thresholds[2]) return 3;
  return 4;
}

export default function Heatmap({ dailyCounts, since, until, selectedDay, onSelectDay }) {
  const weeks = buildWeeks(since, until);
  const thresholds = computeThresholds(dailyCounts);

  let lastMonth = -1;
  const monthMarkers = weeks.map((week) => {
    const firstReal = week.find((d) => d);
    if (!firstReal) return null;
    const month = new Date(`${firstReal}T00:00:00Z`).getUTCMonth();
    if (month !== lastMonth) {
      lastMonth = month;
      return MONTH_LABELS[month];
    }
    return null;
  });

  return (
    <div className="heatmap">
      <div className="heatmap-months">
        {monthMarkers.map((label, i) => (
          <span key={i} className="heatmap-month">
            {label || ""}
          </span>
        ))}
      </div>
      <div className="heatmap-grid">
        {weeks.map((week, wi) => (
          <div className="heatmap-col" key={wi}>
            {week.map((day, di) => {
              if (!day) return <div className="heatmap-cell empty" key={di} />;
              const count = dailyCounts.get(day) || 0;
              const level = levelFor(count, thresholds);
              const isSelected = selectedDay === day;
              return (
                <div
                  key={di}
                  className={`heatmap-cell level-${level} ${isSelected ? "selected" : ""}`}
                  title={`${day}: ${count} activit${count === 1 ? "y" : "ies"}`}
                  onClick={() => onSelectDay(day)}
                />
              );
            })}
          </div>
        ))}
      </div>
      <div className="heatmap-legend">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((level) => (
          <div key={level} className={`heatmap-cell level-${level}`} />
        ))}
        <span>More</span>
        {selectedDay && (
          <button className="clear-day" onClick={() => onSelectDay(selectedDay)}>
            Clear day filter ({selectedDay})
          </button>
        )}
      </div>
    </div>
  );
}
