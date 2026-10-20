# Quick Fix — IT Workbench

## Important: what GitHub Pages can and cannot do

GitHub Pages serves static HTML, CSS and JavaScript. It **cannot run Windows commands on your PC**. This project therefore has two modes:

- **Demo mode:** works as soon as the site is published. The sample readings are explicitly labelled; no pretend result is presented as a real diagnostic.
- **Local agent mode:** an optional Python agent running on your Windows PC provides actual system/network/process data and a small allow-list of actions. The agent binds only to `127.0.0.1`; it is not a cloud backend and should not be exposed to the network.

The agent is deliberately restricted. The browser cannot submit arbitrary shell commands. SFC and DISM require the agent to be started from an Administrator terminal, and the UI requires a separate confirmation before running any maintenance action.

## Features in this first release

- Responsive dark dashboard with optional light theme
- Overview cards for CPU, RAM, drive usage and uptime
- Diagnostics: system information, system health, disk overview, top processes
- Network tools: IP configuration, connectivity context and DNS flush
- Maintenance: SFC, DISM, restart File Explorer and safe temporary-file guidance
- Process table (read-only; no kill-process button)
- Activity history stored in the browser, with JSON export
- Explicit demo/live mode indicators and a local-agent connection test
- Responsive layout for mobile and desktop

Some features from the terminal baseline are intentionally not carried across as destructive one-click actions. Recycle Bin deletion, arbitrary shell commands, and password-gated debug command execution are excluded for safety. They can be redesigned later with safer workflows and auditability.

## Publish on GitHub Pages

1. Create a new GitHub repository, for example `Quick-Fix-Dashboard`.
2. Upload the contents of this project folder to the repository root (so `index.html` is at the root).
3. Open **Settings → Pages**.
4. Set the source to **Deploy from a branch**, choose `main` and `/ (root)`, then save.
5. Wait for the deployment to finish. The site should load at `https://YOUR-USERNAME.github.io/REPOSITORY/`.

No build step is required. This is plain static HTML, CSS and JavaScript.

## Run the local agent on Windows

Use Python 3.10+.

1. Open a terminal in the `agent` folder.
2. Install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Open `quickfix_agent.py` and add your **exact published site origin** to `ALLOWED_ORIGINS`. For a project site, the origin is normally `https://YOUR-USERNAME.github.io` (not the repository path). The default list includes `https://ohaziah.github.io`.
4. Start the agent:

   ```powershell
   python quickfix_agent.py
   ```

5. Keep the terminal open, open the dashboard's GitHub Pages URL in the same browser, select **Connection settings**, and test `http://127.0.0.1:8765`.

For SFC or DISM, start the terminal with **Run as administrator**. Do not run the agent as an administrator for everyday read-only checks unless needed.

### Browser/local-agent notes

Modern browsers may apply local-network access protections to a hosted page requesting `127.0.0.1`. If the browser blocks the connection, demo mode still works. Browser policies can change; this first release does not include a bundled desktop shell or a remote server.

## Security model

- The local agent binds to loopback only (`127.0.0.1`), not `0.0.0.0`.
- Cross-origin requests are restricted to the configured origin allow-list.
- The API exposes fixed routes and fixed commands only.
- POST actions require a confirmation payload.
- The dashboard never offers arbitrary shell execution or automatic process termination.
- The browser history stays in that browser's local session; no telemetry or cloud data collection is implemented.
- This is a personal toolkit starter, not a hardened enterprise management agent. Review the code before using it on a production endpoint.

## Test checklist

### Static site
- [ ] Open `index.html` locally or publish it with GitHub Pages.
- [ ] Navigate through every sidebar page.
- [ ] Confirm demo labels are visible and sample data is not described as live.
- [ ] Run demo actions; check output and activity history.
- [ ] Export activity as JSON and toggle light mode.
- [ ] Test the mobile layout.

### Local agent
- [ ] Install `psutil` from `agent/requirements.txt`.
- [ ] Start the agent and open `http://127.0.0.1:8765/api/status` locally.
- [ ] Configure the exact GitHub Pages origin in `ALLOWED_ORIGINS`.
- [ ] Connect from the dashboard and check the live badge.
- [ ] Verify SFC/DISM are blocked without an elevated terminal.
- [ ] Confirm every POST action requires explicit confirmation.
- [ ] Test with a standard non-admin user before relying on the agent.

## Project structure

```text
quickfix-dashboard/
├── index.html
├── .nojekyll
├── README.md
├── assets/
│   ├── app.js
│   ├── favicon.svg
│   └── styles.css
└── agent/
    ├── quickfix_agent.py
    └── requirements.txt
```

## Future roadmap

- Signed installer for the local agent and automatic startup option
- Exportable HTML/PDF support report
- Searchable troubleshooting playbooks and script library
- Better event-log viewer with filtering and date ranges
- Disk SMART and Windows service status where supported
- User-configurable tool cards and saved device profiles
- Unit tests for API routes and Windows action wrappers
- Optional desktop shell if browser local-network restrictions become a blocker


## Expanded workbench features

- Live monitoring refreshes CPU, memory and primary-drive readings at a configurable 5, 10, 30 or 60 second interval while the dashboard remains open.
- Theme studio presets: Midnight, Ocean, Violet, Emerald, Graphite and Light, plus a custom accent colour. Theme preferences are stored in the current browser only.
- Read-only Windows diagnostics for recent critical/error events from System and Application logs, selected common service status, recent installed hotfixes and basic DNS/TCP reachability.
- Searchable technician toolkit with network, Windows, app and hardware troubleshooting guides.
- JSON support-report export from the Activity & reports page. Review the file for device names, IP addresses, process names and event messages before sharing it.

The extended diagnostics live in `agent/extended_diagnostics.py`, beside `quickfix_agent.py`; keep both files in the same `agent` folder when downloading or copying the agent.
