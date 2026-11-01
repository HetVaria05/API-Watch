# APIWatch – API Testing & Monitoring Tool

> A lightweight, self-hosted alternative to basic API testing tools. Built with Python, FastAPI, and vanilla JavaScript.

---

## ✨ Features

| Feature | Description |
|---|---|
| **API Tester** | Send GET, POST, PUT, PATCH, DELETE requests with custom headers, body, and query params |
| **Response Validation** | Define assertions: status code, body text, JSON key, JSON key-value, response time |
| **Collections** | Save, organize, edit, and re-run API requests in named collections |
| **Request History** | SQLite-backed history with search, filter, and detailed response view |
| **Monitoring** | Register endpoints, check availability manually, view uptime % |
| **Reports** | Export CSV reports and view summary statistics |
| **Modern UI** | Dark-themed single-page frontend with sidebar navigation |

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI 0.104 |
| HTTP Client | HTTPX (async) |
| Database | SQLite + SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Testing | Pytest, respx (HTTP mocking) |

---

## 📸 Screenshots

> Run the project and visit `http://localhost:8000` to see the live UI.

| Section | Description |
|---|---|
| Dashboard | Stats cards + recent activity |
| API Tester | Request builder with tabs for headers/body/params/assertions |
| Collections | Cards with saved requests, execute and delete |
| Monitoring | Endpoint cards with uptime bars |
| History | Filterable table with detail modal |
| Reports | Summary stats + CSV download |

---

## ⚡ Installation

### 1. Clone / open the project
```bash
cd "d:\API Testing & Monitoring Tool\apiwatch"
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# or
source venv/bin/activate     # Linux/macOS
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Application

```bash
# From the apiwatch/ directory:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in your browser.

- Interactive API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

---

## 🧪 Running Tests

```bash
# From the apiwatch/ directory:
pytest -v
```

Expected: all tests pass with mocked HTTP responses (no internet required).

---

## 📡 API Endpoint Reference

### API Tester
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/requests/send` | Send an HTTP request |

### History
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/history/` | List history (filter: method, search) |
| GET | `/api/history/{id}` | Get single history record |
| DELETE | `/api/history/{id}` | Delete a record |
| DELETE | `/api/history/` | Clear all history |

### Collections
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/collections/` | List all collections |
| POST | `/api/collections/` | Create collection |
| GET | `/api/collections/{id}` | Get collection |
| PUT | `/api/collections/{id}` | Update collection |
| DELETE | `/api/collections/{id}` | Delete collection |
| POST | `/api/collections/requests` | Add saved request |
| PUT | `/api/collections/requests/{id}` | Update saved request |
| DELETE | `/api/collections/requests/{id}` | Delete saved request |
| POST | `/api/collections/requests/{id}/execute` | Execute saved request |

### Monitoring
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/monitoring/endpoints` | List endpoints with uptime |
| POST | `/api/monitoring/endpoints` | Register endpoint |
| PUT | `/api/monitoring/endpoints/{id}` | Update endpoint |
| DELETE | `/api/monitoring/endpoints/{id}` | Remove endpoint |
| POST | `/api/monitoring/endpoints/{id}/check` | Manual check |
| POST | `/api/monitoring/check-all` | Check all endpoints |
| GET | `/api/monitoring/endpoints/{id}/checks` | List check history |

### Reports
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/reports/csv` | Download CSV report |
| GET | `/api/reports/summary` | Get summary statistics |
| GET | `/api/reports/dashboard` | Dashboard data |

---

## 🏗 Project Structure

```
apiwatch/
├── app/
│   ├── main.py          # FastAPI app, CORS, route registration
│   ├── database.py      # SQLAlchemy engine and session
│   ├── models.py        # ORM models (5 tables)
│   ├── schemas.py       # Pydantic schemas
│   ├── routes/
│   │   ├── requests.py  # API tester endpoint
│   │   ├── history.py   # History CRUD
│   │   ├── collections.py # Collections CRUD
│   │   ├── monitoring.py  # Monitoring CRUD + checks
│   │   └── reports.py   # CSV + stats
│   └── services/
│       ├── api_client.py  # HTTPX request sender + SSRF protection
│       ├── validator.py   # Response assertion engine
│       ├── monitor.py     # Endpoint health checker
│       └── report_generator.py # CSV and stats
├── frontend/
│   ├── index.html       # Single-page app
│   ├── style.css        # Dark theme
│   └── script.js        # All frontend logic
├── tests/
│   ├── conftest.py      # In-memory DB fixtures
│   ├── test_api_client.py
│   ├── test_validator.py
│   └── test_routes.py
├── data/                # SQLite DB stored here
├── tasks/plan.md        # Implementation plan
├── requirements.txt
├── pyproject.toml       # Pytest config
└── README.md
```

---

## ⚠️ Known Limitations

- SQLite is not suitable for high-concurrency production use
- No authentication (single-user tool)
- Background monitoring must be triggered manually
- Response bodies are truncated at 50 KB
- Localhost/127.0.0.1 is allowed by default (for local development); remove this exception for production

---

## 🔮 Future Improvements

- [ ] JWT authentication and user accounts
- [ ] Automatic scheduled monitoring with configurable intervals
- [ ] WebSocket for real-time monitoring updates
- [ ] Environment variables support (dev/staging/prod)
- [ ] Import/export collections as JSON
- [ ] Response diff viewer (compare two responses)
- [ ] GraphQL support
- [ ] PostgreSQL support for production

---

## 🔒 Security Notes

- SSRF protection: private, link-local, and reserved IP addresses are blocked by default
- Sensitive headers (`Authorization`, `Cookie`) are redacted before being stored in history
- All database queries use SQLAlchemy's parameterized operations (no raw SQL)
- Request bodies are parsed safely — malformed JSON returns an error, not a crash
- Timeouts are enforced on every outbound HTTP request (30 seconds)
