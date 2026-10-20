"""Read-only supplemental diagnostics for the Quick Fix local agent."""
import json
import os
import socket
import subprocess
from datetime import datetime

def _powershell_json(script, timeout=25):
    if os.name != "nt":
        return {"available": False, "message": "This diagnostic is only available on Windows."}
    try:
        cp = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=timeout, check=False, shell=False,
        )
        if cp.returncode:
            return {"available": False, "message": (cp.stderr or cp.stdout or "PowerShell query failed")[-3000:]}
        raw = cp.stdout.strip()
        if not raw:
            return {"available": True, "items": []}
        parsed = json.loads(raw)
        return {"available": True, "items": parsed if isinstance(parsed, list) else [parsed]}
    except subprocess.TimeoutExpired:
        return {"available": False, "message": "The diagnostic timed out."}
    except (OSError, ValueError) as exc:
        return {"available": False, "message": str(exc)}

def events():
    script = r"""$ErrorActionPreference='Stop'; Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); Level=@(1,2); StartTime=(Get-Date).AddDays(-7)} -MaxEvents 40 -ErrorAction SilentlyContinue | Select-Object @{n='time';e={$_.TimeCreated.ToString('o')}},Id,LevelDisplayName,ProviderName,LogName,Message | ConvertTo-Json -Depth 3 -Compress"""
    result = _powershell_json(script, 30)
    result["description"] = "Up to 40 recent critical/error events from System and Application logs, covering the last 7 days."
    return result

def services():
    script = r"""$ErrorActionPreference='Stop'; Get-Service | Where-Object {$_.Name -in @('Dnscache','Dhcp','Spooler','BITS','wuauserv','WinDefend','W32Time','EventLog')} | Sort-Object Name | Select-Object Name,DisplayName,Status,StartType | ConvertTo-Json -Depth 2 -Compress"""
    result = _powershell_json(script, 20)
    result["description"] = "Read-only status of selected common Windows services. A stopped service is not automatically a fault."
    return result

def updates():
    script = r"""$ErrorActionPreference='Stop'; Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 20 HotFixID,Description,InstalledBy,@{n='InstalledOn';e={if($_.InstalledOn){$_.InstalledOn.ToString('yyyy-MM-dd')}else{$null}}} | ConvertTo-Json -Depth 2 -Compress"""
    result = _powershell_json(script, 25)
    result["description"] = "Recent installed hotfixes reported by Get-HotFix; not a complete Windows Update compliance report."
    return result

def connectivity():
    result = {"tested_at": datetime.now().isoformat(timespec="seconds"), "dns": False, "tcp_443": False, "target": "1.1.1.1:443", "notes": ["Basic reachability checks only; not a full proxy, VPN or application health assessment."]}
    try:
        socket.getaddrinfo("example.com", 443)
        result["dns"] = True
    except OSError as exc:
        result["dns_error"] = str(exc)
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=3):
            result["tcp_443"] = True
    except OSError as exc:
        result["tcp_error"] = str(exc)
    return result
