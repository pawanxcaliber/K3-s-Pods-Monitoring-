# Distributed Observability Stack with K3s, Prometheus, Loki & Grafana

## 📖 Overview
This project demonstrates a production-grade **Observability Stack** deployed on a hybrid **2-Node Kubernetes (K3s) Cluster**. The system monitors hardware metrics (CPU/RAM) and aggregates application logs across two physical laptops acting as a distributed infrastructure.

The goal was to simulate a real-world **On-Premise Data Center** environment where a "Control Plane" manages resources and observability for "Worker Nodes."

---

## 🏗️ Architecture Design

### Physical Infrastructure

#### **Node 1 (Dep System): pawan-aspire-a311-45**
*   **Role:** Control Plane (Master) & Storage Backend.
*   **Services Hosted:** K3s Server, Grafana, Prometheus Server, Loki (Log Database).
*   **IP:** `10.84.106.126`

#### **Node 2 (Dev System): pawan-aspire-a715-42g**
*   **Role:** Worker Node.
*   **Services Hosted:** Workloads, Node Exporter (Metrics Agent), Promtail (Log Collector).
*   **IP:** `10.84.106.68`

### Data Flow
1.  **Metrics:** Node Exporter (on all nodes) → Scraped by Prometheus (on Master) → Visualized in Grafana.
2.  **Logs:** Promtail (on all nodes) → Pushed to Loki (on Master) → Visualized in Grafana.

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

## 🔧 Troubleshooting Log (The "Real" Experience)
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

This setup replicates a standard SRE / DevOps environment for monitoring distributed microservices.
