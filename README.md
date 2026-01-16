# Distributed Observability Stack with K3s, Prometheus, Loki, Grafana & Tempo

## 📖 Overview
This project demonstrates a production-grade **Observability Stack** deployed on a hybrid **2-Node Kubernetes (K3s) Cluster**. The system monitors hardware metrics (CPU/RAM), aggregates application logs, and traces distributed transactions across two physical laptops acting as a distributed infrastructure.

The goal was to simulate a real-world **On-Premise Data Center** environment where a "Control Plane" manages resources and observability for "Worker Nodes."

Screenshot: 
<img width="1913" height="940" alt="image" src="https://github.com/user-attachments/assets/6831876e-e24e-48ae-9d70-f65c5d57f57c" />

---

## 🏗️ Architecture Design

### Physical Infrastructure

#### **Node 1 (Dep System): pawan-aspire-a311-45**
*   **Role:** Control Plane (Master) & Storage Backend.
*   **Services Hosted:** K3s Server, Grafana, Prometheus Server, Loki (Log Database), Tempo (Distributed Tracing).
*   **IP:** `10.84.106.126`

#### **Node 2 (Dev System): pawan-aspire-a715-42g**
*   **Role:** Worker Node.
*   **Services Hosted:** Workloads, Node Exporter (Metrics Agent), Promtail (Log Collector).
*   **IP:** `10.84.106.68`

### Data Flow
1.  **Metrics:** Node Exporter (on all nodes) → Scraped by Prometheus (on Master) → Visualized in Grafana.
2.  **Logs:** Promtail (on all nodes) → Pushed to Loki (on Master) → Visualized in Grafana.
3.  **Traces:** OpenTelemetry/Tempo (on Master) → Visualized in Grafana (mapped to Logs).

---

## 🛠️ Installation & Configuration

### Step 1: Cluster Initialization
We utilized **K3s** for a lightweight Kubernetes implementation.

**On Master (Dep System):**
```bash
# Install K3s Master
curl -sfL https://get.k3s.io | sh -

# Get the Join Token
sudo cat /var/lib/rancher/k3s/server/node-token
```

**On Worker (Dev System):**
```bash
# Join the cluster
curl -sfL https://get.k3s.io | K3S_URL=https://10.84.106.126:6443 K3S_TOKEN=<YOUR_TOKEN> sh -
```

### Step 2: Deploying the Monitoring Stack
We used `kubectl` to deploy the components into a dedicated namespace `monitoring`.

1.  **Create Namespace:**
    ```bash
    sudo kubectl create namespace monitoring
    ```

2.  **Deploy Prometheus & Grafana (via Helm/Manifests):**
    *   **Prometheus:** Configured to scrape `kubernetes-nodes` and `kubernetes-pods`.
    *   **Grafana:** Exposed via ClusterIP.

3.  **Deploy Loki (Log Aggregation):**
    *   Loki requires persistent storage. We used a `StatefulSet`.
    *   **Service Name:** `loki`
    *   **Port:** `3100`
    *   **Config:** No Authentication (Internal Cluster Mode).

4.  **Deploy Promtail (Log Collector):**
    *   Deployed as a **DaemonSet** so it runs on every node automatically to collect logs from `/var/log/pods`.

---

## 💻 Key Commands Reference

**Check Cluster Health:**
```bash
sudo kubectl get nodes -o wide
```

**Check Observability Pods:**
```bash
sudo kubectl get pods -n monitoring -o wide
```

**Access Grafana UI (Port Forwarding):**
```bash
sudo kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring --address 0.0.0.0
```

**Verify Internal Connectivity (Debugging):**
```bash
# Run a curl command from inside the cluster to test Loki
sudo kubectl exec -it <grafana-pod-name> -n monitoring -- curl http://loki.monitoring:3100/ready
```

---

## 📊 Grafana Configuration & Dashboard

### Data Source Setup
1.  **Prometheus:**
    *   **URL:** `http://prometheus-operated:9090` (Internal DNS)
    *   **Access:** Server (Default)

2.  **Loki:**
    *   **URL:** `http://loki.monitoring:3100`
    *   **HTTP Method:** POST (Managed implicitly or via config)
    *   **Validation:** Verified via "Explore" tab even when Test button failed.

### Master Dashboard Queries
We combined Metrics and Logs into a single **"Single Pane of Glass"** view.

| Panel Title | Visualization | Query (PromQL / LogQL) |
| :--- | :--- | :--- |
| **CPU Usage** | Time Series | `100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| **RAM Usage** | Time Series | `node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes` |
| **Live Logs** | Logs | `{job="monitoring/loki"}` |

---

## 🧩 Extended Configuration & Demo

### 1. ⏱️ Tempo Configuration (Tracing)
We implemented distributed tracing using **Grafana Tempo**.
*   **File:** [`tempo-values.yaml`](tempo-values.yaml)
*   **Key Configs:**
    *   **Storage:** Local filesystem (`/var/tempo/traces`).
    *   **Receivers:** OTLP gRPC (`4317`) and HTTP (`4318`).
    *   **Tolerations:** Configured to schedule on the Master node despite taints.

### 2. 🪵 Loki Internal Configuration
Custom configuration for the Loki instance running inside the cluster.
*   **File:** [`loki.yaml`](loki.yaml)
*   **Settings:**
    *   **Auth:** Disabled (Multi-tenant disabled).
    *   **Retention:** 0s (Forever) - *Monitor disk usage carefully!*
    *   **Storage:** Filesystem with BoltDB shipper.

### 3. 🚕 HotROD Demo App
A vehicle route planning application to demonstrate distributed tracing.
*   **File:** [`hotrod.yaml`](hotrod.yaml)
*   **Deployment:**
    *   **Image:** `grafana/hotrod:latest`
    *   **Tracing:** Configured to point to `tempo.monitoring`.
    *   **Access:** Exposed via ClusterIP `8080`.
    *   **Apply:** `kubectl apply -f hotrod.yaml`

### 4. 📊 Grafana Datasources (Internal)
Mappings for the datasources in the Grafana UI:
1.  **Prometheus:** `http://prometheus-operated:9090`
2.  **Loki:** `http://loki:3100`
3.  **Tempo:** `http://tempo.monitoring:3200`

---

## �️ Distributed Tracing with Grafana Tempo & K3s

### 1. Prerequisites (Fixing Permissions)
Before running Helm, ensure your user (`pawan`) has access to the cluster config without using `sudo` for every command.

```bash
# Create local kube directory
mkdir -p ~/.kube

# Copy K3s config and take ownership
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
chmod 600 ~/.kube/config

# Set env variable (Add this to ~/.bashrc to make permanent)
export KUBECONFIG=~/.kube/config
```

### 2. Install Grafana Tempo (The Backend)
#### A. Add Grafana Helm Repo
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

#### B. Create Configuration File (tempo-values.yaml)
This configuration does three critical things:
1.  **Storage:** Uses local disk (no S3 needed).
2.  **Ports:** Opens `4317` (gRPC) and `4318` (HTTP) for traces.
3.  **Taints:** Allows Tempo to run on your "Control Plane" node despite the high-performance taint.

*   **File Created:** [`tempo-values.yaml`](tempo-values.yaml)

#### C. Deploy Tempo
If a broken installation exists, delete it first:
```bash
sudo kubectl delete statefulset tempo -n monitoring
```
Install the new version:
```bash
helm upgrade --install tempo grafana/tempo -f tempo-values.yaml -n monitoring
```

**Verify Status:**
```bash
kubectl get pods -n monitoring -l app.kubernetes.io/name=tempo
# Wait for: 1/1 Running
```

### 3. Configure Grafana (The Frontend)
1.  Open Grafana: `http://<YOUR_IP>:3000`
2.  Go to **Connections > Data Sources > Add new data source**.
3.  Search for **Tempo**.
4.  **Settings:**
    *   **URL:** `http://tempo.monitoring:3200` *(Note: Port 3200 is for reading, 4317 is for writing)*.
5.  **Trace to logs:**
    *   **Data source:** Loki
    *   **Tags:** `job`
6.  Click **Save & test**.

### 4. Instrumenting Python (The Test Script)
We run this script on the Master Node. Because newer Linux versions block global pip installs, we use a virtual environment.

#### A. Setup Python Environment
```bash
# 1. Install venv tool (if missing)
sudo apt install python3.12-venv -y

# 2. Create sandbox
python3 -m venv trace-test

# 3. Activate sandbox
source trace-test/bin/activate

# 4. Install OpenTelemetry libraries
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

#### B. Create the Script (test_trace.py)
This script generates a sample trace with a parent span and a child span.
*   **File:** [`test_trace.py`](test_trace.py)

#### C. Run the Test
**Terminal 1 (The Tunnel):** Keep this running to allow the script to talk to the cluster.
```bash
sudo kubectl port-forward svc/tempo 4317:4317 -n monitoring --address 0.0.0.0
```

**Terminal 2 (The Script):**
```bash
source trace-test/bin/activate  # Ensure venv is active
python3 test_trace.py
```

---

## �🔧 Troubleshooting Log (The "Real" Experience)
This project faced several infrastructure hurdles. Here is how we solved them:

### 1. The "Pending" Loki Pod (Taint Issue)
*   **Problem:** The `loki-0` pod was stuck in `Pending` state.
*   **Cause:** The Master node had a "NoSchedule" taint to prevent workloads from slowing it down.
*   **Fix:** We patched the Loki StatefulSet to tolerate the master node:
    ```bash
    kubectl patch statefulset loki -n monitoring --patch '{"spec":{"template":{"spec":{"tolerations":[{"key":"hardware","operator":"Equal","value":"high-performance","effect":"NoSchedule"}]}}}}'
    ```

### 2. Disk Pressure & Eviction (Dev System)
*   **Problem:** Pods on the Worker node (`promtail`, `node-exporter`) kept showing status `Evicted` or `ImagePullBackOff`.
*   **Cause:** The laptop ran out of disk space, triggering K3s eviction policies.
*   **Fix:** Cleaned unused container images and restarted the agent:
    ```bash
    sudo k3s crictl rmi --prune
    sudo systemctl restart k3s-agent
    ```

### 3. The Grafana "Unable to Connect" Loop
*   **Problem:** Grafana UI showed `400 Bad Request` or `Unable to connect` when adding Loki, even though the pod was running.
*   **Cause:** Grafana's "Test" button sends a specific health query that sometimes fails on specific versions, and browser-based HTTP methods were restricted.
*   **Fix:**
    *   Verified backend health manually: `curl http://loki.monitoring:3100/ready`.
    *   Bypassed the "Test" button error.
    *   Went directly to the **Explore** tab and ran a valid query `{job="monitoring/loki"}` to confirm data was actually flowing.

### 4. Syntax Errors in LogQL
*   **Problem:** `parse error at line 1... unexpected IDENTIFIER`.
*   **Cause:** We attempted to put a full LogQL query `{job="..."}` into the simple "Text filter" box in Grafana Builder mode.
*   **Fix:** Switched to **Code Mode** in Grafana Explore and entered the raw query.

---

## 🚀 Final Result
The system is now fully operational. We can observe:
*   **Hardware Spikes:** Correlate high CPU usage on the Worker node.
*   **Application Errors:** Immediately see logs from the containers causing those spikes in the same window.
*   **Distributed Traces:** Follow a request from the frontend to the database using Tempo, linked directly from the logs.

This setup replicates a standard SRE / DevOps environment for monitoring distributed microservices.
