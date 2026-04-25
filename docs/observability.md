# Observability Stack

Centralized logging, metrics, and distributed tracing for the EFKO Kernel microservices platform.

## Components

| Component | Purpose | Host Port |
|-----------|---------|-----------|
| **Grafana** | Unified UI for logs, metrics, and traces | 3101 |
| **Prometheus** | Metrics storage and query engine | 9090 |
| **Loki** | Log aggregation from Pino | 3100 |
| **Jaeger** | Distributed trace storage and UI | 16686 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  docker-compose.observability.yml            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Grafana  │  │  Loki    │  │  Jaeger  │  │ Prometheus   │ │
│  │  :3101   │  │  :3100   │  │  :16686  │  │   :9090      │ │
│  └────┬─────┘  └──────────┘  └──────────┘  └──────────────┘ │
│       │                                                      │
│       │ Queries Loki for logs, Prometheus for metrics        │
│       │ Shows Jaeger traces embed via links                  │
└───────┼──────────────────────────────────────────────────────┘
        │           shared network (efko-kernel_default)
        │
┌───────┴──────────────────────────────────────────────────────┐
│                     docker-compose.yml (existing)             │
│  ┌─────────┐  ┌─────────────┐  ┌──────────┐                  │
│  │ gateway │  │ personnel   │  │ auth-svc │  ...              │
│  │  :3000  │  │   :3003     │  │  :3001   │                  │
│  └────┬────┘  └──────┬──────┘  └────┬─────┘                  │
│       │              │              │                         │
│       └──────────────┼──────────────┘                         │
│                      RabbitMQ                                 │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start all infrastructure (including observability)

```bash
npm run obs:up
```

This starts PostgreSQL, RabbitMQ, MongoDB, Grafana, Prometheus, Loki, and Jaeger in detached mode.

### 2. Start microservices (in separate terminals)

```bash
nx serve gateway
nx serve auth-service
nx serve etl
nx serve personnel
nx serve production
```

### 3. Access Grafana

Open http://localhost:3101

Default credentials (from `.env`):
- Username: `admin`
- Password: `admin`

Pre-configured dashboards:
- **EFKO Service Overview** — HTTP request rate, latency (p95), error rate, service health
- **Logs Explorer** — search logs by service and text
- **Distributed Traces** — trace list via Jaeger datasource links

### 4. Stop everything

```bash
npm run obs:down
```

## Component Details

### Loki (Log Aggregation)

- **Port**: 3100
- **Config**: `docker/loki/loki-config.yml`
- **Purpose**: Collects structured JSON logs from all services via `pino-loki` transport
- **Labels**: Each log entry is tagged with `service_name` (gateway, auth-service, etl, personnel, production)

### Prometheus (Metrics)

- **Port**: 9090
- **Config**: `docker/prometheus/prometheus.yml`
- **Purpose**: Scrapes `/metrics` endpoints from all NestJS services
- **Targets**: localhost:3000/metrics (gateway), localhost:3001/metrics (auth-service), etc.
- **Metrics**: HTTP request duration/count, Node.js event loop lag, memory usage, GC stats

### Jaeger (Distributed Tracing)

- **Port**: 16686 (UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP)
- **Purpose**: Stores and visualizes distributed traces across HTTP requests and RabbitMQ messages
- **Instrumentation**: OpenTelemetry auto-instrumentation for HTTP, Express, and amqplib

### Grafana (Visualization)

- **Port**: 3101 (host) → 3000 (container)
- **Provisioning**: `docker/grafana/provisioning/datasources/datasources.yml`
- **Dashboards**: `docker/grafana/dashboards/efko-overview.json`

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Observability endpoints
GRAFANA_HOST_PORT=3101
LOKI_HOST=http://localhost:3100
JAEGER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
OTEL_SERVICE_NAME=efko-gateway

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### Log Levels

Set `LOG_LEVEL` environment variable to control verbosity:
- `debug` — all logs including traces (default for dev)
- `info` — operational events
- `warn` — warnings only
- `error` — errors only

## Production Considerations

1. **Sampling**: In production, configure `OTEL_TRACES_SAMPLER=parentbased_traceidratio` and `OTEL_TRACES_SAMPLER_ARG=0.1` to sample only 10% of traces.

2. **Metrics port**: Consider exposing `/metrics` on a separate internal port (not the public API port) to avoid exposing internal metrics.

3. **Loki retention**: In production, configure Loki with persistent storage and retention policies (default is ephemeral in dev).

4. **Grafana auth**: Change default admin password and disable anonymous access.

## Files

| File | Description |
|------|-------------|
| `docker-compose.observability.yml` | Docker Compose for observability stack |
| `docker/loki/loki-config.yml` | Loki configuration |
| `docker/prometheus/prometheus.yml` | Prometheus scrape targets |
| `docker/grafana/provisioning/datasources/datasources.yml` | Grafana datasource auto-config |
| `docker/grafana/dashboards/efko-overview.json` | Pre-built dashboard |
| `libs/nest-utils/src/tracing/tracing.ts` | OpenTelemetry bootstrap |
| `libs/nest-utils/src/metrics/metrics.module.ts` | Prometheus metrics module |
