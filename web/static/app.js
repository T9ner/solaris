document.addEventListener("DOMContentLoaded", async () => {
  const caseSelect = document.getElementById("case-select");
  const runBtn = document.getElementById("run-btn");
  const logViewer = document.getElementById("log-viewer");
  const discrepanciesList = document.getElementById("discrepancies-list");
  const briefBox = document.getElementById("brief-box");

  // Load benchmark summary metrics
  try {
    const res = await fetch("/api/benchmarks");
    const data = await res.json();
    if (data.detection_rate_pct !== undefined) {
      document.getElementById("stat-detection").innerText = `${data.detection_rate_pct.toFixed(1)}%`;
      document.getElementById("stat-fp").innerText = `${data.false_positive_rate_pct.toFixed(1)}%`;
      document.getElementById("stat-time").innerText = `${data.avg_time_seconds}s`;
    }
  } catch (e) {
    console.error("Could not load benchmarks:", e);
  }

  runBtn.addEventListener("click", async () => {
    const caseId = caseSelect.value;
    runBtn.disabled = true;
    runBtn.innerText = "Executing Pipeline...";

    logViewer.innerHTML = `<div class="log-line"><span class="time">[START]</span> Launching Forge Pipeline for ${caseId}...</div>`;
    discrepanciesList.innerHTML = `<div style="color: var(--text-secondary); font-size: 13px;">Sensing cross-system signals across GitHub, Linear, Stripe, Sentry, and Web...</div>`;
    briefBox.innerText = "Compiling executive briefing...";

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId, use_mock: true, auto_approve: true }),
      });

      const result = await response.json();

      // Render Trajectories Log
      logViewer.innerHTML = "";
      if (result.trajectories) {
        result.trajectories.forEach((t) => {
          const div = document.createElement("div");
          div.className = "log-line";
          div.innerHTML = `<span class="time">[${t.timestamp.split("T")[1].replace("Z", "")}]</span> <span class="node">${t.node}</span>: ${t.description}`;
          logViewer.appendChild(div);
        });
        logViewer.scrollTop = logViewer.scrollHeight;
      }

      // Render Discrepancies
      if (!result.discrepancies || result.discrepancies.length === 0) {
        discrepanciesList.innerHTML = `<div style="color: var(--accent-green); font-size: 13px; font-weight: 600;">✓ Zero discrepancies detected. All tools are in perfect synchronization.</div>`;
      } else {
        discrepanciesList.innerHTML = "";
        result.discrepancies.forEach((d) => {
          const card = document.createElement("div");
          card.className = `discrepancy-card ${d.severity}`;
          card.innerHTML = `
            <div class="title">[${d.severity.toUpperCase()}] ${d.title}</div>
            <div class="desc">${d.description}</div>
            <div class="action">Action: ${d.recommended_action}</div>
          `;
          discrepanciesList.appendChild(card);
        });
      }

      // Render Brief
      if (result.executive_brief) {
        briefBox.innerText = result.executive_brief;
      }
    } catch (err) {
      logViewer.innerHTML += `<div class="log-line" style="color: var(--accent-red);">Error: ${err.message}</div>`;
    } finally {
      runBtn.disabled = false;
      runBtn.innerText = "Run Autonomous Pipeline";
    }
  });
});
