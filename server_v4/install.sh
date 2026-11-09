#!/usr/bin/env bash
set -euo pipefail
BASE='https://raw.githubusercontent.com/ivadialsan-bit/ivadi-content-factory/main/server_v4'
INSTALL_DIR='/opt/contentfactory-v4'
DATA_DIR='/var/lib/contentfactory-v4'
if [[ "$EUID" -ne 0 ]]; then echo 'Run as root';exit 1; fi
if [[ -e "$INSTALL_DIR/app.py" ]]; then
  echo 'Existing installation detected. Saving previous app.py backup.'
  cp "$INSTALL_DIR/app.py" "$INSTALL_DIR/app.py.bak.$(date +%s)"
fi
id contentfactory-v4 &>/dev/null || useradd -r -M -d "$DATA_DIR" -s /usr/sbin/nologin contentfactory-v4
mkdir -p "$INSTALL_DIR/agents" "$DATA_DIR"
chmod 750 "$INSTALL_DIR" "$INSTALL_DIR/agents"
curl -fsSL --max-time 45 "$BASE/app.py" -o "$INSTALL_DIR/app.py"
curl -fsSL --max-time 45 "$BASE/carousel.py" -o "$INSTALL_DIR/carousel.py"
curl -fsSL --max-time 45 "$BASE/agents/roles.json" -o "$INSTALL_DIR/agents/roles.json"
python3 -m py_compile "$INSTALL_DIR/app.py" "$INSTALL_DIR/carousel.py"
chown -R root:contentfactory-v4 "$INSTALL_DIR"
chmod 640 "$INSTALL_DIR/app.py" "$INSTALL_DIR/carousel.py" "$INSTALL_DIR/agents/roles.json"
chown -R contentfactory-v4:contentfactory-v4 "$DATA_DIR"
chmod 750 "$DATA_DIR"
if [[ ! -f /etc/contentfactory-v4.env ]]; then
  cat > /etc/contentfactory-v4.env <<'EOF'
CF_DATA_DIR=/var/lib/contentfactory-v4
CF_PORT=8765
CF_AUTOPOST=0
CF_AUTO_GENERATE=0
# CF_ACCOUNT_ID=your_account_id
# CF_WORKERS_AI_TOKEN=save_secret_here
# CF_TG_BOT_TOKEN=save_secret_here
# CF_TG_CHAT_ID=@your_channel
EOF
fi
chown root:contentfactory-v4 /etc/contentfactory-v4.env
chmod 640 /etc/contentfactory-v4.env
cat > /etc/systemd/system/contentfactory-v4.service <<'EOF'
[Unit]
Description=Content Factory OS v4 (loopback-only)
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=contentfactory-v4
Group=contentfactory-v4
WorkingDirectory=/opt/contentfactory-v4
EnvironmentFile=/etc/contentfactory-v4.env
ExecStart=/usr/bin/python3 /opt/contentfactory-v4/app.py serve
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/contentfactory-v4
PrivateTmp=true
UMask=0077
MemoryMax=420M
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
runuser -u contentfactory-v4 -- env CF_DATA_DIR="$DATA_DIR" python3 "$INSTALL_DIR/app.py" init
systemctl enable --now contentfactory-v4.service
sleep 2
printf '\n=== CONTENT FACTORY 4.0 INSTALL RESULT ===\n'
systemctl is-active contentfactory-v4.service
curl -fsS --max-time 10 'http://127.0.0.1:8765/api/status'; echo
printf '\nPANEL: http://127.0.0.1:8765 (LOOPBACK ONLY)\n'
printf 'NO MODEL CREDITS REQUIRED FOR SETUP\n'