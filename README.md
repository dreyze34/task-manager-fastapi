# Task Manager FastAPI

An asynchronous job queue system built with Python, a FastAPI API, Redis,
and independent workers. The project implements job management mechanisms
without Celery or RQ.

## How it works

1. The client submits a job to the API.
2. The API stores the job in a Redis Hash (`job:<id>`) and adds its
   identifier to the `jobs:queue` Stream.
3. A worker in the `workers` consumer group retrieves the message and
   executes the corresponding handler.
4. The worker saves the result or error before acknowledging the message.
5. The client checks the job's status and result through the API.

A job moves from `pending` to `running`, then to `completed` or `failed`.
The `attempts` field is incremented when the job enters the `running` state.

## Prerequisites

- Python 3.11 or later (the code uses `StrEnum`).
- Docker with Docker Compose to start Redis, or a local Redis server.
- Port `6379` available for Redis and port `8000` for the API.

## Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi 'pydantic>=2,<3' redis uvicorn
python -m pip install -r requirements-test.txt
```

Application dependencies do not yet have a dedicated requirements file.
`requirements-test.txt` contains the HTTP dependency used by the tests.

## Running locally

### 1. Redis

```bash
docker compose up -d redis
```

The Compose file starts Redis 7.4 at `127.0.0.1:6379`, with AOF persistence
in the `redis_data` volume. It only starts Redis; the API and workers are
started separately.

### 2. API

In a terminal, from the project root:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

- API: <http://127.0.0.1:8000>
- Swagger documentation: <http://127.0.0.1:8000/docs>
- ReDoc documentation: <http://127.0.0.1:8000/redoc>

The API connects to `redis://localhost:6379/0` and checks the connection at
startup. This address is currently defined in `app/main.py`.

### 3. Worker

In another terminal, from the same project root:

```bash
source .venv/bin/activate
python -m app.workers
```

Each worker processes one job at a time. To run multiple workers, execute
this command in multiple terminals. Each process receives a unique
identifier and shares the same consumer group.

The worker accepts the `REDIS_URL` environment variable, which defaults to
`redis://localhost:6379/0`. No additional configuration is needed for the
local setup above. The API does not yet read this variable; both processes
must use the same Redis server and database.

## Using the API

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status": "ok"}`. |
| `POST` | `/jobs` | Creates a job and returns its details (currently HTTP `200`). |
| `GET` | `/jobs` | Lists stored jobs, without pagination or guaranteed ordering. |
| `GET` | `/jobs/{job_id}` | Returns a job, or HTTP `404` if it cannot be found. |

### Submit a job

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"type":"add","payload":{"a":10,"b":20}}'
```

The response contains the `id`, `type`, `payload`, `status`, `result`,
`error`, and `attempts` fields. Use the returned `id` to retrieve the job:

```bash
curl http://127.0.0.1:8000/jobs/<job_id>
```

Once this example has been processed, its status is `completed`, its result
is `30`, and its attempt count is `1`. Without an active worker, the job
remains pending.

### Available job types

| Type | Example payload | Result |
| --- | --- | --- |
| `add` | `{"a":10,"b":20}` | Sum of the two values: `30`. |
| `fibonacci` | `{"n":10}` | Fibonacci sequence term: `55`. |
| `sleep` | `{"seconds":2}` | Waits for the requested duration, then returns `null`. |

A handler error moves the job to `failed`, with details in `error`.
For example, `fibonacci` rejects negative integers.

## Tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

The tests use in-memory implementations and a simulated Redis client.
They do not require a running Redis or Uvicorn server and do not validate
the production Redis connection. Some tests use `expectedFailure` to track
gaps against the intended contract. See [tests/README.md](tests/README.md)
for details about the test suite.

## Project structure

```text
app/
├── main.py                  # FastAPI application and Redis connection
├── dependencies.py          # Service injection into routes
├── api/jobs.py              # Job creation and retrieval routes
├── models/job.py            # Pydantic models and statuses
├── services/                # Business logic for jobs and workers
├── storage/                 # Storage interface and Redis Hashes adapter
├── queue/                   # Queue interface and Redis Streams adapter
└── workers/                 # Entry point, processing loop, and handlers
tests/                       # API, service, worker, and adapter tests
docker-compose.yml           # Local Redis server
ARCHITECTURE.md              # Target architecture and future improvements
```

## Current limitations

- Job creation returns HTTP `200`; the target architecture calls for `202`.
- Job types are checked at creation, but the corresponding domain error
  is not yet mapped to a dedicated HTTP response. Payloads are not validated
  against each handler's signature before being queued.
- Saving a job and enqueueing it are separate operations without an atomic
  transaction.
- Unacknowledged messages are not automatically recovered after a crash.
  There are no automatic retries or heartbeats.
- Cancellation, priorities, and scheduling are not implemented.
- Jobs and Stream messages have no cleanup policy.
- `/health` returns a static response rather than continuously checking Redis.

[ARCHITECTURE.md](ARCHITECTURE.md) describes the project's goals, so some
proposals go beyond the features currently available.

## Shutdown

Stop the API and workers with `Ctrl+C`, then stop Redis:

```bash
docker compose down
```

The Redis volume is retained for the next startup.
