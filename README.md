# GridSense

GridSense is a prototype smart power grid analytics and fault-management system developed for the Advanced Data Management final assessment.

The application combines multiple database technologies behind a single FastAPI REST API. Each datastore handles a different part of the grid data, while Redis provides caching and live alert handling. Prometheus collects API metrics and Grafana provides an automatically provisioned observability dashboard.

## Running GridSense

### Requirements

The project requires:

- Docker
- Docker Compose

All application services, databases, initialization scripts, seed data, monitoring components, and dashboards run through Docker Compose.

### Environment configuration

Create a local `.env` file from the provided template.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

The `.env` file contains the local credentials and connection strings used by the containers.

Replace the `change_me` values before starting the system.

### Start the complete system

From the repository root run:

```bash
docker compose up --build
```

During startup Docker Compose:

1. Starts Redis, PostgreSQL, MongoDB, Neo4j, and Cassandra.
2. Waits for the required database health checks.
3. Runs the Cassandra schema initialization container.
4. Runs the GridSense seed container.
5. Starts the FastAPI application after seeding completes.
6. Starts Prometheus.
7. Starts Grafana with a GridSense dashboard automatically provisioned.

Cassandra normally takes the longest to become healthy during a clean first startup.

## Services

| Service           | Function                                        |        Port |
| ----------------- | ----------------------------------------------- | ----------: |
| FastAPI           | GridSense REST API                              |        8000 |
| Cassandra 4.1     | Sensor time-series storage                      |        9042 |
| Neo4j 5 Community | Electrical grid topology                        | 7474 / 7687 |
| MongoDB 7         | Equipment metadata catalogue                    |       27017 |
| PostgreSQL 15     | Consumer accounts and invoices                  |        5432 |
| Redis 7           | Sensor-summary cache, active alerts and Pub/Sub |        6379 |
| Prometheus        | API metrics collection                          |        9090 |
| Grafana           | API observability dashboard                     |        3000 |

Two one-shot containers are also used during startup:

- `cassandra-init` applies the Cassandra schema after Cassandra becomes healthy.
- `seed` populates Cassandra, Neo4j, MongoDB, and PostgreSQL before the API starts.

## Service Access

FastAPI:

```text
http://localhost:8000
```

Swagger/OpenAPI documentation:

```text
http://localhost:8000/docs
```

Prometheus:

```text
http://localhost:9090
```

Grafana:

```text
http://localhost:3000
```

The Grafana username is:

```text
admin
```

The password is the value configured as `GRAFANA_PASSWORD` in `.env`.

## Data Initialization

GridSense uses a single master seed process:

```text
scripts/seed.py
```

The script initializes the data required by the prototype in all four persistent databases.

The seed operation is idempotent. Running it again produces the same seeded dataset rather than intentionally creating duplicate seed records.

### Cassandra sensor data

Cassandra is populated with:

- 30 sensor IDs
- 2,000 readings per sensor
- 60,000 readings in total
- 5-second reading intervals
- voltage, current and power-factor measurements
- quality flags

The same generated reading is stored in both Cassandra access patterns used by the application.

`sensor_readings` stores readings by sensor and time.

`sensor_readings_by_bucket` stores readings using time buckets and four deterministic shards for time-oriented access.

The timestamps used for the seed are deterministic, so repeating the seed writes the same Cassandra rows.

### Neo4j grid topology

The Neo4j seed contains:

- 2 Grid Supply Points
- 10 substations
- 40 transformers
- 200 smart meters

The main topology follows:

```text
GridSupplyPoint
    ↓ FEEDS
Substation
    ↓ SUPPLIES
Transformer
    ↓ CONNECTS_TO
SmartMeter
```

Each topology object has a common `node_id`, allowing the API to traverse different node types through the same identifier.

`GSP_NORTH` provides the main active supply topology.

`GSP_BACKUP` and several additional relationships are also included in the seed as inactive redundant paths. These relationships use the same `FEEDS`, `SUPPLIES`, and `CONNECTS_TO` relationship types but have `active = false`.

As a result, restore-path queries can return both the normal path and available alternative topology paths and indicate whether every relationship in a returned path is currently active.

Neo4j nodes and relationships are created with `MERGE`, allowing the seed to be executed repeatedly without duplicating the seeded topology.

### MongoDB equipment catalogue

MongoDB contains 30 equipment records across three equipment types:

- 10 SmartMeters
- 10 Transformers
- 10 Switchgear units

The records intentionally have different document shapes.

For example, SmartMeter documents contain fields such as firmware version, rated voltage, phase, and protocol, while Transformer documents contain rating and cooling information and Switchgear documents contain breaking capacity and insulation information.

The equipment API accepts additional fields beyond the common equipment identifiers, preserving MongoDB's flexible document structure.

The seed uses an upsert by `asset_id`, so running it again replaces the corresponding seed document rather than adding another copy.

### PostgreSQL billing data

PostgreSQL is populated with:

- 100 consumer accounts
- one initial sample invoice for each account

The seed uses deterministic premise IDs such as:

```text
PREM_10001
PREM_10002
...
```

Accounts are inserted or updated by `premise_id`.

The sample invoice seed checks for an existing invoice for the same premise and due date before inserting it, allowing the PostgreSQL seed to be executed repeatedly.

## REST API

### Sensor telemetry

#### `POST /sensors/readings`

Stores one sensor reading or a batch of readings in Cassandra.

Each reading contains:

- sensor ID
- timestamp
- metric type
- value
- unit
- quality flag

The API writes the data into both Cassandra tables used by GridSense.

#### `GET /sensors/{sensor_id}/readings`

Returns readings for a sensor.

Supported parameters include:

```text
limit
from_time
```

#### `GET /sensors/{sensor_id}/summary`

Returns a one-hour summary containing:

- latest reading
- measurement count
- average
- minimum
- maximum

The generated summary is cached in Redis for 30 seconds using a key based on the sensor ID.

If the key already exists, the API returns the cached summary. Otherwise it obtains the data from Cassandra, calculates the summary, stores it in Redis with a 30-second expiration, and returns it.

### Grid topology

#### `GET /grid/fault-impact/{node_id}`

Traverses the Neo4j topology downstream from the supplied node.

The response contains affected nodes, their type, their traversal depth, and the total number of affected nodes.

Traversal depth is bounded through the `max_depth` parameter.

#### `GET /grid/restore-paths/{node_id}`

Finds supply paths from a Grid Supply Point to the requested node.

Each returned path contains:

- source Grid Supply Point
- ordered list of node IDs
- number of hops
- active state

A path is marked active only when all relationships forming that path have `active = true`.

Because the seeded topology also contains redundant inactive connections, this endpoint can return both main and alternative supply paths when they exist.

#### `POST /grid/nodes`

Creates a new Neo4j topology node.

Supported node types are:

```text
GridSupplyPoint
Substation
Transformer
SmartMeter
```

Each node type has its own required properties while sharing the common `node_id` and `name` fields.

#### `POST /grid/relationships`

Creates a topology relationship between existing nodes.

Supported relationship types are:

```text
FEEDS
SUPPLIES
CONNECTS_TO
```

The API validates the node types for each relationship:

```text
GridSupplyPoint -> Substation    FEEDS
Substation      -> Transformer   SUPPLIES
Transformer     -> SmartMeter    CONNECTS_TO
```

Relationships also contain an `active` state.

### Equipment catalogue

#### `POST /equipment`

Creates a MongoDB equipment document.

The common required fields are:

```text
asset_id
equipment_type
```

Additional equipment-specific fields are accepted and stored in the same document.

#### `GET /equipment/{asset_id}`

Returns the complete MongoDB equipment document associated with the requested asset ID.

#### `PATCH /equipment/{asset_id}`

Updates only the supplied equipment fields.

Existing fields not included in the PATCH request remain unchanged.

The MongoDB `_id` and application `asset_id` identifiers cannot be changed through the PATCH endpoint.

### Billing

#### `GET /billing/account/{premise_id}`

Returns account information together with the current outstanding balance.

The outstanding balance is calculated from invoices belonging to the account whose status is:

```text
UNPAID
```

#### `POST /billing/invoice`

Creates an invoice for an existing account.

The invoice contains:

- premise ID
- amount
- payment status
- due date

Invoice creation is performed inside a PostgreSQL transaction.

The API first verifies that the requested account exists and then inserts the invoice.

### Alerts

#### `POST /alerts/publish`

Creates a new alert in Redis.

An alert contains:

- alert ID
- node ID
- tag
- alarm type
- limit
- current value
- priority
- message
- state
- timestamp

Supported alarm types are:

```text
HH
H
L
LL
```

Redis maintains an incrementing sequence used to generate IDs such as:

```text
ALR-000001
ALR-000002
```

A newly published alert has:

```text
state = ACTIVE
```

The alert is stored in the Redis active-alert hash and the same event is published to the Redis `alerts` Pub/Sub channel.

#### `GET /alerts/active`

Returns all alerts currently stored in the Redis active-alert hash together with the number of active alerts.

Alerts remain ACTIVE until explicitly cleared.

#### `POST /alerts/{alert_id}/clear`

Clears an existing active alert.

The endpoint loads the active alert, changes its state to:

```text
CLEARED
```

updates its timestamp, removes it from the active-alert hash, and publishes the CLEARED event to the same Redis `alerts` Pub/Sub channel.

After an alert has been cleared it no longer appears in:

```text
GET /alerts/active
```

## API Observability

Every FastAPI request is instrumented with Prometheus metrics.

The raw metrics are exposed at:

```text
GET /metrics
```

Prometheus scrapes this endpoint every five seconds.

The request instrumentation provides metrics used to calculate:

- request count
- request rate
- server error rate
- request duration
- latency percentiles

Grafana uses Prometheus as its automatically provisioned datasource.

The `GridSense API Observability` dashboard is also provisioned automatically when Grafana starts.

The dashboard contains:

- Total API Requests
- Request Count by Endpoint
- Request Rate by Endpoint
- Server Error Rate by Endpoint
- p50 Latency by Endpoint
- p95 Latency by Endpoint
- p99 Latency by Endpoint

The dashboard uses a default 30-minute time range and a five-second refresh interval.

Prometheus's own requests to `/metrics` are excluded from the GridSense API request panels.

## Health Endpoint

GridSense exposes:

```text
GET /health
```

A healthy API returns:

```json
{
  "status": "healthy"
}
```

This provides a simple application-level check that the FastAPI service is running.

## Example API Calls

The following examples can be executed after the system has started.

### Read sensor data

```bash
curl "http://localhost:8000/sensors/SM_00001/readings?limit=10"
```

### Get a sensor summary

```bash
curl "http://localhost:8000/sensors/SM_00001/summary"
```

### Calculate fault impact

```bash
curl "http://localhost:8000/grid/fault-impact/GSP_NORTH?max_depth=6"
```

### Find supply and restore paths

```bash
curl "http://localhost:8000/grid/restore-paths/SM_00001?max_depth=6"
```

### Read equipment metadata

```bash
curl "http://localhost:8000/equipment/SM_00001"
```

### Read a billing account

```bash
curl "http://localhost:8000/billing/account/PREM_10001"
```

### Publish an alert

```bash
curl -X POST "http://localhost:8000/alerts/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "TX_001_A",
    "tag": "temperature",
    "alarm_type": "HH",
    "limit": 90,
    "value": 96.4,
    "priority": 1,
    "message": "Transformer temperature high"
  }'
```

### List active alerts

```bash
curl "http://localhost:8000/alerts/active"
```

### Clear an alert

Replace `ALR-000001` with the ID returned by the publish request.

```bash
curl -X POST "http://localhost:8000/alerts/ALR-000001/clear"
```

## Stopping and Resetting GridSense

Stop the running containers while preserving database volumes:

```bash
docker compose down
```

Start them again with:

```bash
docker compose up --build
```

To remove all persistent Docker volumes and return the prototype to a completely clean state:

```bash
docker compose down -v
```

The next:

```bash
docker compose up --build
```

will recreate the databases, initialize Cassandra, run the complete seed process, start the API, and recreate the Prometheus/Grafana monitoring environment automatically.
