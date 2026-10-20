"""
Quick Fix local Windows agent.
Listens only on 127.0.0.1. Exposes a small allow-list of diagnostics and actions.
Do not bind to 0.0.0.0 or expose this service to a network.
"""
from __future__ import annotations
import json, os, platform, shutil, socket, subprocess, time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    import psutil
except ImportError:
    psutil = None

HOST = "127.0.0.1"
PORT = 8765
# Replace this with your published GitHub Pages origin, e.g. https://yourname.github.io
ALLOWED_ORIGINS = {
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://ohaziah.github.io",
}
MAX_BODY = 4096

def is_windows():
    return os.name == "nt"

def admin():
    if not is_windows(): return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def system_info():
    result = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "processor": platform.processor() or "Unavailable",
        "uptime": "Unavailable",
        "cpu_percent": 0,
        "ram_total_gb": 0,
        "ram_used_percent": 0,
        "ram_used_gb": 0,
        "disks": [],
        "local_ip": "Unavailable",
        "admin": admin(),
        "demo": False,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }
    if psutil:
        result["cpu_percent"] = psutil.cpu_percent(interval=0.35)
        vm = psutil.virtual_memory()
        result["ram_total_gb"] = round(vm.total / 1024**3, 1)
        result["ram_used_percent"] = vm.percent
        result["ram_used_gb"] = round(vm.used / 1024**3, 1)
        result["uptime"] = str(timedelta(seconds=max(0, int(time.time()-psutil.boot_time())))).split(".")[0]
        for part in psutil.disk_partitions(all=False):
            if not part.mountpoint or "cdrom" in part.opts.lower(): continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                result["disks"].append({"mount":part.mountpoint,"total_gb":round(usage.total/1024**3,1),"used_gb":round(usage.used/1024**3,1),"free_gb":round(usage.free/1024**3,1),"percent":usage.percent})
            except (PermissionError, OSError):
                pass
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        result["local_ip"] = sock.getsockname()[0]
        sock.close()
    except OSError:
        try: result["local_ip"] = socket.gethostbyname(socket.gethostname())
        except OSError: pass
    return result

def network_info():
    data = {"hostname":socket.gethostname(),"local_ip":"Unavailable","gateway":"Use ipconfig for details","dns":[],"internet":"Not tested","demo":False}
    if psutil:
        for addresses in psutil.net_if_addrs().values():
            for addr in addresses:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    data["local_ip"] = addr.address
                    break
    if is_windows():
        try:
            completed = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=10, check=False)
            data["ipconfig"] = completed.stdout[-12000:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            data["ipconfig_error"] = str(exc)
    return data

def processes():
    if not psutil: return {"processes":[]}
    rows=[]
    for p in psutil.process_iter(["pid","name","memory_info"]):
        try:
            info=p.info
            rows.append({"name":info.get("name") or "Unknown","pid":info["pid"],"cpu_percent":p.cpu_percent(interval=None),"memory_mb":round((info.get("memory_info").rss if info.get("memory_info") else 0)/1024**2)})
        except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess):
            continue
    rows.sort(key=lambda x:x["memory_mb"],reverse=True)
    return {"processes":rows[:30],"collected_at":datetime.now().isoformat(timespec="seconds")}

def run_allowlisted(action):
    if not is_windows():
        return {"ok":False,"message":"This action is only supported on Windows."}, 400
    if action == "flushdns":
        cmd=["ipconfig","/flushdns"]
        timeout=30
    elif action == "sfc":
        if not admin(): return {"ok":False,"message":"Run the agent from an Administrator terminal to use SFC."}, 403
        cmd=["sfc","/scannow"]; timeout=1800
    elif action == "dism":
        if not admin(): return {"ok":False,"message":"Run the agent from an Administrator terminal to use DISM."}, 403
        cmd=["DISM","/Online","/Cleanup-Image","/RestoreHealth"]; timeout=3600
    elif action == "explorer":
        # Explicitly allowlisted, but still restarts the shell.
        subprocess.run(["taskkill","/f","/im","explorer.exe"],capture_output=True,text=True,timeout=15,check=False)
        subprocess.Popen(["explorer.exe"],close_fds=True)
        return {"ok":True,"message":"File Explorer restart requested. Open windows may close briefly.","action":action}, 200
    else:
        return {"ok":False,"message":"Action is not allow-listed."}, 404
    try:
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False,shell=False)
        output=(cp.stdout+"\n"+cp.stderr).strip()[-10000:]
        return {"ok":cp.returncode==0,"message":f"Command finished with exit code {cp.returncode}.","action":action,"return_code":cp.returncode,"output":output}, 200
    except subprocess.TimeoutExpired:
        return {"ok":False,"message":f"{action} timed out. The command may still have made changes."}, 504
    except OSError as exc:
        return {"ok":False,"message":str(exc)}, 500

class Handler(BaseHTTPRequestHandler):
    server_version = "QuickFixAgent/1.0"
    def log_message(self, fmt, *args):
        print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), fmt % args))
    def _origin(self):
        return self.headers.get("Origin", "")
    def _cors(self):
        origin=self._origin()
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
    def _json(self, payload, status=200):
        body=json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def do_OPTIONS(self):
        origin=self._origin()
        if origin not in ALLOWED_ORIGINS:
            self._json({"error":"Origin not allowed. Add your exact GitHub Pages origin to ALLOWED_ORIGINS."},403); return
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self._origin() and self._origin() not in ALLOWED_ORIGINS:
            self._json({"error":"Origin not allowed."},403); return
        path=urlparse(self.path).path
        if path=="/api/status": self._json({"service":"quickfix-agent","version":"1.0.0","windows":is_windows(),"admin":admin(),"psutil":bool(psutil)})
        elif path=="/api/diagnostics/system": self._json(system_info())
        elif path=="/api/diagnostics/network": self._json(network_info())
        elif path=="/api/processes": self._json(processes())
        else: self._json({"error":"Endpoint not found."},404)
    def do_POST(self):
        if self._origin() and self._origin() not in ALLOWED_ORIGINS:
            self._json({"error":"Origin not allowed."},403); return
        if self._origin() not in ALLOWED_ORIGINS:
            self._json({"error":"POST requires an allow-listed browser origin."},403); return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length<0 or length>MAX_BODY: self._json({"error":"Request body too large."},413); return
            payload=json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"error":"Invalid JSON body."},400); return
        if payload.get("confirmed") is not True:
            self._json({"error":"Explicit confirmation is required."},400); return
        action=urlparse(self.path).path.removeprefix("/api/actions/")
        result,status=run_allowlisted(action)
        self._json(result,status)

def main():
    if not is_windows():
        print("Warning: Quick Fix Agent is designed for Windows. Read-only endpoints may be limited.")
    print(f"Quick Fix Agent listening at http://{HOST}:{PORT}")
    print("Keep this terminal open. Do not expose the service to your network.")
    print("Allowed origins:", ", ".join(sorted(ALLOWED_ORIGINS)))
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopping Quick Fix Agent...")
    finally: server.server_close()

if __name__=="__main__":
    main()
