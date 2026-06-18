#!/usr/bin/env python3
"""
Servidor local — Bongarbit Dashboard.
Uso:  python3 serve.py           → porta 8080
      python3 serve.py 3000      → porta customizada
      python3 serve.py --build   → reconstrói antes de servir
"""
import http.server, socketserver, subprocess, sys, os, webbrowser
from pathlib import Path

PORT  = next((int(a) for a in sys.argv[1:] if a.isdigit()), 8080)
ROOT  = Path(__file__).parent

if "--build" in sys.argv:
    print("Gerando dashboard...")
    subprocess.run([sys.executable, "build_dashboard.py"], check=True)

os.chdir(ROOT)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

print(f"\n🥁 Bongarbit Dashboard  →  http://localhost:{PORT}/")
print("   Ctrl+C para parar\n")
webbrowser.open(f"http://localhost:{PORT}/")

with socketserver.TCPServer(("", PORT), Handler) as s:
    try:   s.serve_forever()
    except KeyboardInterrupt: print("\nEncerrado.")
