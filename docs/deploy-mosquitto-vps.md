# Deploy Mosquitto on a VPS for Wokwi MQTT

Use this guide when hosted Wokwi needs a stable MQTT broker. Hosted Wokwi cannot connect to your local Docker `localhost`, so the stable setup is a public Mosquitto broker on a VPS.

## Recommended architecture

```text
Hosted Wokwi ESP32 MicroPython
  ↓ MQTT telemetry/state
mqtt.example.com:8883 — Mosquitto on VPS
  ↑ MQTT commands
Local or deployed FastAPI/NiceGUI app
```

Start with broker-only deployment. Deploying the full app later is possible, but the broker-only step solves remote Wokwi MQTT with less operational work.

## What you need

- VPS with Ubuntu 22.04 or 24.04
- Domain or subdomain, for example `mqtt.example.com`
- SSH access to the VPS
- Docker and Docker Compose plugin on the VPS
- Strong MQTT passwords for at least two users:
  - `app` — backend publishes commands and reads telemetry/state
  - `wokwi` — Wokwi publishes telemetry/state and reads commands

Recommended VPS size:

```text
1 vCPU
1 GB RAM
10–20 GB disk
Ubuntu 24.04 LTS
```

## DNS

Create an `A` record:

```text
mqtt.example.com  A  <VPS_PUBLIC_IPV4>
```

Optional if your VPS has IPv6:

```text
mqtt.example.com  AAAA  <VPS_PUBLIC_IPV6>
```

Wait until DNS resolves:

```bash
dig +short mqtt.example.com
```

## VPS firewall

Open SSH and MQTT over TLS:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8883/tcp
sudo ufw enable
sudo ufw status
```

Avoid exposing plain MQTT `1883` publicly unless this is a temporary test.

## Install Docker on VPS

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in, then verify:

```bash
docker --version
docker compose version
```

## Broker directory layout

On the VPS:

```bash
mkdir -p ~/greenhouse-mqtt/{config,certs,data,log}
cd ~/greenhouse-mqtt
```

Target layout:

```text
greenhouse-mqtt/
  compose.yml
  config/
    mosquitto.conf
    acl.conf
    passwordfile
  certs/
    fullchain.pem
    privkey.pem
  data/
  log/
```

## Create Mosquitto config

Create `config/mosquitto.conf`:

```conf
persistence true
persistence_location /mosquitto/data

log_dest stdout
log_timestamp true

allow_anonymous false
password_file /mosquitto/config/passwordfile
acl_file /mosquitto/config/acl.conf

listener 8883
protocol mqtt
certfile /mosquitto/certs/fullchain.pem
keyfile /mosquitto/certs/privkey.pem
```

Create `config/acl.conf`:

```conf
user app
topic readwrite greenhouse-groups/#

user wokwi
topic read greenhouse-groups/+/greenhouses/+/zones/+/commands
topic write greenhouse-groups/+/greenhouses/+/zones/+/telemetry
topic write greenhouse-groups/+/greenhouses/+/zones/+/state
```

This keeps Wokwi limited to device topics while the app can read/write the project MQTT hierarchy.

## Create password file

Create it through the Mosquitto image so the hash format is correct:

```bash
touch config/passwordfile
docker run --rm -it \
  -v "$PWD/config/passwordfile:/passwordfile" \
  eclipse-mosquitto:2.1.2-alpine \
  mosquitto_passwd -c /passwordfile app

docker run --rm -it \
  -v "$PWD/config/passwordfile:/passwordfile" \
  eclipse-mosquitto:2.1.2-alpine \
  mosquitto_passwd /passwordfile wokwi
```

Use strong unique passwords. Store them in your password manager.

## TLS certificates

### Option 1: Use Caddy to obtain certs separately

If you already use Caddy on the VPS, copy or mount the certificate files into `certs/fullchain.pem` and `certs/privkey.pem`.

### Option 2: Use Certbot standalone

Stop anything using port `80`, then:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d mqtt.example.com
sudo cp /etc/letsencrypt/live/mqtt.example.com/fullchain.pem certs/fullchain.pem
sudo cp /etc/letsencrypt/live/mqtt.example.com/privkey.pem certs/privkey.pem
sudo chown -R "$USER:$USER" certs
chmod 600 certs/privkey.pem
```

Renewal note: after renewal, copy the renewed files again and restart Mosquitto:

```bash
docker compose restart mosquitto
```

You can automate that later with a deploy hook.

## Docker Compose on VPS

Create `compose.yml`:

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2.1.2-alpine
    container_name: greenhouse-mqtt
    restart: unless-stopped
    ports:
      - "8883:8883"
    volumes:
      - ./config/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - ./config/acl.conf:/mosquitto/config/acl.conf:ro
      - ./config/passwordfile:/mosquitto/config/passwordfile:ro
      - ./certs:/mosquitto/certs:ro
      - ./data:/mosquitto/data
      - ./log:/mosquitto/log
    healthcheck:
      test: ["CMD-SHELL", "mosquitto_sub -h localhost -p 8883 --cafile /mosquitto/certs/fullchain.pem -u app -P '$$MQTT_APP_PASSWORD' -t 'greenhouse-groups/healthcheck' -C 1 -W 3 >/tmp/mqtt-healthcheck.out & pid=$$!; mosquitto_pub -h localhost -p 8883 --cafile /mosquitto/certs/fullchain.pem -u app -P '$$MQTT_APP_PASSWORD' -t 'greenhouse-groups/healthcheck' -m ok; wait $$pid"]
      interval: 30s
      timeout: 10s
      retries: 3
    environment:
      MQTT_APP_PASSWORD: ${MQTT_APP_PASSWORD}
```

Create `.env` on the VPS:

```env
MQTT_APP_PASSWORD=change-this-app-password
```

This password is only used by the container healthcheck. It must match the `app` password in `passwordfile`.

Start broker:

```bash
docker compose up -d
docker compose ps
docker compose logs -f mosquitto
```

## Test from your local machine

Install clients locally if needed:

```bash
sudo apt install -y mosquitto-clients
```

Terminal 1:

```bash
mosquitto_sub \
  -h mqtt.example.com \
  -p 8883 \
  --capath /etc/ssl/certs \
  -u app \
  -P 'change-this-app-password' \
  -t 'greenhouse-groups/+/greenhouses/+/zones/+/telemetry' \
  -v
```

Terminal 2:

```bash
mosquitto_pub \
  -h mqtt.example.com \
  -p 8883 \
  --capath /etc/ssl/certs \
  -u wokwi \
  -P 'change-this-wokwi-password' \
  -t 'greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry' \
  -m '{"message_id":"manual-check-1","qos":0,"reading":{"group_id":"group-001","greenhouse_id":"gh-001","zone_id":"zone-01","sensor_id":"manual","metric":"temperature","value":24.5,"quality":"ok","timestamp":"2026-05-16T12:00:00Z"}}'
```

If Terminal 1 receives the message, broker routing works.

## Configure local app to use VPS broker

In project `.env` on your local machine:

```env
MQTT_HOST=mqtt.example.com
MQTT_PORT=8883
MQTT_USERNAME=app
MQTT_PASSWORD=change-this-app-password
```

Restart app:

```bash
docker compose up -d --build app
```

Check status:

```bash
curl http://127.0.0.1:8080/api/mqtt/status
```

Expected fields:

```json
{
  "running": true,
  "connected": true,
  "subscribed_topic": "greenhouse-groups/+/greenhouses/+/zones/+/telemetry",
  "broker_host": "mqtt.example.com",
  "broker_port": 8883,
  "error_count": 0
}
```

## Configure Wokwi firmware

In `firmware/wokwi-greenhouse-zone/config.py`:

```python
MQTT_HOST = "mqtt.example.com"
MQTT_PORT = 8883
MQTT_USER = "wokwi"
MQTT_PASSWORD = "change-this-wokwi-password"

GROUP_ID = "group-001"
GREENHOUSE_ID = "gh-001"
ZONE_ID = "zone-01"
```

Start hosted Wokwi. Confirm serial output shows:

```text
Wi-Fi connected
MQTT connected
Subscribed to greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/commands
```

Then check the app MQTT status panel for received telemetry.

## Security checklist

- Do not expose `1883` publicly for production.
- Use TLS on `8883`.
- Use `allow_anonymous false`.
- Use strong unique passwords.
- Keep app and Wokwi on separate users.
- Limit Wokwi ACL to telemetry/state writes and command reads.
- Keep real credentials out of git.
- Back up `config/passwordfile`, `config/acl.conf`, and cert renewal setup.

## Backups

Broker data is less important than app DB data, but keep configuration backed up:

```bash
tar czf greenhouse-mqtt-config-$(date +%F).tar.gz config compose.yml .env
```

Store the archive outside the VPS or in your password manager/secure backup storage.

## Monitoring commands

```bash
docker compose ps
docker compose logs --tail=100 mosquitto
sudo ufw status
ss -tulpn | grep 8883
```

Subscribe to all greenhouse traffic as app user for debugging:

```bash
mosquitto_sub -h mqtt.example.com -p 8883 --capath /etc/ssl/certs -u app -P 'change-this-app-password' -t 'greenhouse-groups/#' -v
```

## Should you deploy the full app too?

Deploying the broker first is the smallest useful step. Full app deployment is reasonable later if you want the dashboard available from anywhere.

### Broker-only deployment

Pros:

- Solves hosted Wokwi connectivity.
- Keeps local app workflow.
- Minimal VPS resources.
- No public web app, Postgres, or InfluxDB operations yet.

Cons:

- Local app must be running to view dashboard and process commands.
- You still manage app locally.

### Full app deployment

Additional pieces:

- `greenhouse.example.com` DNS record.
- HTTPS reverse proxy, such as Caddy.
- Postgres and InfluxDB volumes/backups.
- App container environment secrets.
- Alembic migrations during deploy.
- Monitoring and log rotation.

High-level full deployment shape:

```text
greenhouse.example.com → Caddy → app:8080
mqtt.example.com:8883 → Mosquitto
app → Postgres
app → InfluxDB
app → Mosquitto
Wokwi → Mosquitto
```

Recommended path:

1. Deploy Mosquitto only.
2. Verify Wokwi telemetry reaches local app through VPS broker.
3. Verify commands from local app reach Wokwi.
4. Add full app deployment only when you need remote dashboard access.
5. Before full deployment, define backup and restore steps for Postgres and InfluxDB.
