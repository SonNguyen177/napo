import { useState } from "react";

export default function CommLogs({ logs }) {
  const [expanded, setExpanded] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const allLogs = logs || [];
  const filtered =
    filter === "ALL"
      ? allLogs
      : allLogs.filter((l) => l.message_type === filter);
  const display = filtered.slice(-100).reverse();

  const messageTypes = [...new Set(allLogs.map((l) => l.message_type))];

  return (
    <div className="card comm-logs">
      <div className="card-header">
        <h2>Communication Logs ({filtered.length})</h2>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="ALL">All Types</option>
          {messageTypes.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Dir</th>
              <th>Client</th>
              <th>Type</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {display.map((log, i) => (
              <>
                <tr
                  key={i}
                  className={`log-row ${log.direction.toLowerCase()}`}
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  style={{ cursor: log.fix_raw ? "pointer" : "default" }}
                >
                  <td>{new Date(log.timestamp * 1000).toLocaleTimeString()}</td>
                  <td>
                    <span className={`dir-badge ${log.direction.toLowerCase()}`}>
                      {log.direction}
                    </span>
                  </td>
                  <td>{log.client_id}</td>
                  <td>{log.message_type}</td>
                  <td>{log.summary}</td>
                </tr>
                {expanded === i && log.fix_raw && (
                  <tr key={`${i}-fix`} className="fix-row">
                    <td colSpan="5">
                      <code className="fix-raw">{log.fix_raw}</code>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {display.length === 0 && (
              <tr>
                <td colSpan="5" className="empty">No logs</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
