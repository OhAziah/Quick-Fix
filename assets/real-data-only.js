/* Real-data-only dashboard guard. Never fabricate readings when the local agent is unavailable. */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const agentBase = () => ($("#agentUrl")?.value || "http://127.0.0.1:8765").trim().replace(/\/+$/, "");
  let connected = false;
  let refreshTimer = null;
  let latest = null;
  const unavailable = "—";

  function clearReadings(message = "WAITING FOR AGENT") {
    connected = false;
    latest = null;
    ["cpuValue", "ramValue", "diskValue"].forEach(id => { const el = $("#" + id); if (el) el.textContent = unavailable; });
    ["cpuMeter", "ramMeter", "diskMeter"].forEach(id => { const el = $("#" + id); if (el) el.style.width = "0%"; });
    ["cpuFoot", "ramFoot", "diskFoot"].forEach(id => { const el = $("#" + id); if (el) el.textContent = "Unavailable — connect the local agent"; });
    if ($("#uptimeValue")) $("#uptimeValue").textContent = unavailable;
    if ($("#hostValue")) $("#hostValue").textContent = "No connected device";
    if ($("#lastUpdated")) $("#lastUpdated").textContent = message;
    if ($("#healthBadge")) $("#healthBadge").textContent = "OFFLINE";
    ["health1Desc", "health2Desc", "health3Desc"].forEach(id => { if ($("#" + id)) $("#" + id).textContent = "Unavailable — no live data"; });
    ["health1Status", "health2Status", "health3Status"].forEach(id => { if ($("#" + id)) { $("#" + id).textContent = "Unavailable"; $("#" + id).className = "health-status neutral"; } });
    if ($("#modePill")) $("#modePill").innerHTML = '<span class="status-dot" style="background:var(--orange)"></span> AGENT DISCONNECTED';
    if ($("#sidebarDot")) $("#sidebarDot").style.background = "var(--orange)";
    if ($("#sidebarAgentLabel")) $("#sidebarAgentLabel").textContent = "Local agent disconnected";
    if ($("#sidebarAgentText")) $("#sidebarAgentText").textContent = "Connect the local Windows agent to read real device data.";
    if ($("#demoNotice")) {
      $("#demoNotice").hidden = false;
      $("#demoNotice").querySelector("strong").textContent = "Local agent not connected";
      $("#demoNotice").querySelector("p").textContent = "No system readings are being shown. Connect the local Windows agent to use real diagnostics.";
    }
  }

  function renderSystem(d) {
    latest = d;
    connected = true;
    const cpu = Number.isFinite(Number(d.cpu_percent)) ? Number(d.cpu_percent) : null;
    const ram = Number.isFinite(Number(d.ram_used_percent)) ? Number(d.ram_used_percent) : null;
    const disk = Number.isFinite(Number(d.disks?.[0]?.percent)) ? Number(d.disks[0].percent) : null;
    const setMetric = (value, valueId, meterId, footId, foot) => {
      if ($("#" + valueId)) $("#" + valueId).innerHTML = value === null ? unavailable : Math.round(value) + "<span>%</span>";
      if ($("#" + meterId)) $("#" + meterId).style.width = value === null ? "0%" : Math.min(100, Math.max(0, value)) + "%";
      if ($("#" + footId)) $("#" + footId).textContent = value === null ? "Unavailable from agent" : foot;
    };
    setMetric(cpu, "cpuValue", "cpuMeter", "cpuFoot", "Current reading");
    setMetric(ram, "ramValue", "ramMeter", "ramFoot", d.ram_used_gb == null ? "Current reading" : d.ram_used_gb + " GB in use");
    setMetric(disk, "diskValue", "diskMeter", "diskFoot", d.disks?.[0]?.free_gb == null ? "Current reading" : d.disks[0].free_gb + " GB free");
    if ($("#uptimeValue")) $("#uptimeValue").textContent = d.uptime || unavailable;
    if ($("#hostValue")) $("#hostValue").textContent = d.hostname || unavailable;
    if ($("#healthBadge")) $("#healthBadge").textContent = "LIVE";
    if ($("#health1Desc")) $("#health1Desc").textContent = [d.os, d.hostname].filter(Boolean).join(" · ") || "Reported by local agent";
    if ($("#health2Desc")) $("#health2Desc").textContent = "Local IP: " + (d.local_ip || "Unavailable");
    if ($("#health3Desc")) $("#health3Desc").textContent = d.disks?.[0]?.free_gb == null ? "Storage reading unavailable" : d.disks[0].free_gb + " GB available";
    ["health1Status", "health2Status", "health3Status"].forEach(id => { if ($("#" + id)) { $("#" + id).textContent = "Reported"; $("#" + id).className = "health-status good"; } });
    if ($("#lastUpdated")) $("#lastUpdated").textContent = "UPDATED " + new Date().toLocaleTimeString();
    if ($("#demoNotice")) $("#demoNotice").hidden = true;
    if ($("#modePill")) $("#modePill").innerHTML = '<span class="status-dot" style="background:var(--green)"></span> LOCAL AGENT';
    if ($("#sidebarDot")) $("#sidebarDot").style.background = "var(--green)";
    if ($("#sidebarAgentLabel")) $("#sidebarAgentLabel").textContent = "Local agent connected";
    if ($("#sidebarAgentText")) $("#sidebarAgentText").textContent = "Connected to this PC. Displaying real agent readings.";
  }

  async function api(path, options = {}) {
    const response = await fetch(agentBase() + path, { ...options, cache: "no-store", headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
    if (!response.ok) {
      let message = "Agent returned HTTP " + response.status;
      try { message = (await response.json()).error || message; } catch {}
      throw new Error(message);
    }
    return response.json();
  }

  async function refresh() {
    try {
      const status = await api("/api/status");
      if (status.service !== "quickfix-agent") throw new Error("Quick Fix Agent was not detected.");
      const data = await api("/api/diagnostics/system");
      if (data.demo === true || !data.hostname) throw new Error("The agent did not return a valid live system snapshot.");
      renderSystem(data);
    } catch {
      clearReadings();
    }
  }

  function startMonitor() {
    if (refreshTimer) clearInterval(refreshTimer);
    const seconds = Number($("#refreshInterval")?.value || 10);
    refreshTimer = setInterval(refresh, Math.max(5, seconds) * 1000);
  }

  async function runRealAction(action) {
    const outputTargets = { system: "#diagnosticOutput", health: "#diagnosticOutput", disk: "#diagnosticOutput", quick: "#diagnosticOutput", processes: "#diagnosticOutput", network: "#networkOutput", ip: "#networkOutput", flushdns: "#networkOutput", sfc: "#maintenanceOutput", dism: "#maintenanceOutput", explorer: "#maintenanceOutput", temp: "#maintenanceOutput" };
    const target = outputTargets[action];
    const write = value => { if (target && $(target)) $(target).textContent = value; };
    if (action === "temp") {
      write("No files were changed. Open Windows Settings → System → Storage → Temporary files and review each category before removing anything.");
      document.querySelector('[data-view="maintenance"]')?.click();
      return;
    }
    const readRoutes = { system: "/api/diagnostics/system", health: "/api/diagnostics/system", disk: "/api/diagnostics/system", quick: "/api/diagnostics/system", processes: "/api/processes", network: "/api/diagnostics/network", ip: "/api/diagnostics/network" };
    if (readRoutes[action]) {
      try {
        const data = await api(readRoutes[action]);
        if (data.demo === true) throw new Error("Sample data was rejected; only live agent results are accepted.");
        if (action === "processes") {
          const rows = data.processes || [];
          if ($("#processMode")) $("#processMode").textContent = "LIVE DATA";
          if ($("#processRows")) $("#processRows").innerHTML = rows.map(p => '<tr><td>' + String(p.name ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])) + '</td><td>' + p.pid + '</td><td>' + Number(p.cpu_percent || 0).toFixed(1) + '%</td><td>' + Number(p.memory_mb || 0).toFixed(0) + ' MB</td><td><span class="health-status good">Running</span></td></tr>').join("") || '<tr><td colspan="5" class="table-empty">No processes returned.</td></tr>';
          document.querySelector('[data-view="processes"]')?.click();
        } else if (action === "network" || action === "ip") {
          write(JSON.stringify(data, null, 2));
          document.querySelector('[data-view="network"]')?.click();
        } else {
          renderSystem(data);
          write(JSON.stringify(data, null, 2));
          document.querySelector('[data-view="diagnostics"]')?.click();
        }
      } catch (e) {
        write("Live diagnostic unavailable: " + e.message + "\nConnect the local Windows agent and try again.");
        clearReadings();
      }
      return;
    }
    const prompts = {
      flushdns: "Flush the Windows DNS cache? This changes local resolver state.",
      sfc: "Run Windows System File Checker? This may take several minutes.",
      dism: "Run DISM health restore? This may take a long time and may contact Windows Update.",
      explorer: "Restart File Explorer? Open Explorer windows may close briefly."
    };
    if (!prompts[action] || !window.confirm(prompts[action])) return;
    try {
      const data = await api("/api/actions/" + action, { method: "POST", body: JSON.stringify({ confirmed: true }) });
      write(JSON.stringify(data, null, 2));
    } catch (e) {
      write("Action unavailable: " + e.message + "\nConfirm the local agent is connected. No demo result was generated.");
      clearReadings();
    }
  }

  function removeDuplicateMonitor() {
    $$(".monitor-panel, #liveMonitoring, [data-panel='live-monitoring']").forEach(el => el.remove());
    $$("section.panel, section").forEach(el => {
      const heading = el.querySelector("h2");
      if (heading && heading.textContent.trim().toLowerCase() === "live monitoring") el.remove();
    });
  }

  function init() {
    removeDuplicateMonitor();
    clearReadings();
    document.addEventListener("click", event => {
      const actionButton = event.target.closest("[data-action]");
      const quickButton = event.target.closest("#runQuickCheck");
      if (!actionButton && !quickButton) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      runRealAction(quickButton ? "quick" : actionButton.dataset.action);
    }, true);
    $("#refreshInterval")?.addEventListener("change", startMonitor);
    $("#testAgent")?.addEventListener("click", () => setTimeout(refresh, 50));
    $("#saveAgent")?.addEventListener("click", () => setTimeout(refresh, 100));
    $("#connectBtn")?.addEventListener("click", () => setTimeout(refresh, 50));
    $("#noticeConnect")?.addEventListener("click", () => setTimeout(refresh, 50));
    document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
    refresh();
    startMonitor();
    new MutationObserver(removeDuplicateMonitor).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
