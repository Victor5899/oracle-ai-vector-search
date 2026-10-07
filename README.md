# Oracle AI Vector Search – Smart Document Q&A System

A document question-and-answer system that uses **Oracle AI Vector Search** to store embeddings and retrieve relevant content for user queries.

The React app calls the FastAPI backend. The backend stores vectors in Oracle Autonomous AI Database 26ai and generates answers with the OpenAI API. The frontend never connects to Oracle and never sees API keys.

## Project structure

```
oracle-ai-vector-search/
├── app/                 # FastAPI backend
├── src/                 # Ingestion, retrieval, and answer generation
├── frontend/            # React / Vite interface
├── sql/                 # Oracle SQL
├── data/                # Sample documents
├── requirements.txt
├── render.yaml          # Render backend service
└── .env.example         # Variable names only; copy to .env locally
```

## Prerequisites

- Python 3.11
- Node.js for the frontend
- Access to the existing Oracle Autonomous AI Database
- pip

## Local setup

1. Create and activate a virtual environment:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in the Oracle, wallet, and OpenAI values. Keep `.env` and the wallet directory out of git.

4. Start the API from the repository root:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. In `frontend/`, install dependencies and start the dev server:

   ```bash
   npm install
   npm run dev
   ```

Leave `VITE_API_BASE_URL` blank locally. The Vite dev server proxies `/api` to `VITE_PROXY_TARGET` (default `http://localhost:8000`), so the browser does not make a cross-origin request.

## Deployment

Do not deploy yet from this repository's instructions alone until the wallet and database access steps below are done. No credentials belong in git.

`.env` is for local development. Render and Vercel supply the same variable names in their environments. `load_dotenv` does not override variables that are already set.

### Backend (Render)

Use the repository root as the service root. `render.yaml` defines the service:

- Python 3.11 (`.python-version`)
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Set these in the Render environment, not in the repo:

| Variable | Purpose |
| --- | --- |
| `DB_USER` | Oracle database user |
| `DB_PASSWORD` | Oracle database password |
| `DB_DSN` | Connect descriptor or TNS alias |
| `WALLET_DIR` | Directory that contains the wallet |
| `WALLET_PASSWORD` | Wallet password |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model name used for answers |
| `CORS_ORIGINS` | Deployed frontend origin, or several separated by commas |

`CORS_ORIGINS` must be the exact Vercel origin, such as `https://your-app.example`. A value of `*` is ignored.

The Oracle wallet is not part of the repository. Upload its files to the host (Render secret files land in one directory) and set `WALLET_DIR` to that directory. The connection stays python-oracledb thin mode with mTLS: `config_dir` and `wallet_location` both use `WALLET_DIR`. Do not change the database network or mTLS settings in Oracle Cloud from this app. The database access control list must already allow this host, or the connection will fail.

The API process imports the embedding model. Give the Render instance enough memory for that model and for PyTorch.

### Frontend (Vercel)

- Root directory: `frontend`
- Framework: Vite
- Build command: `npm run build`
- Output directory: `dist`

Set `VITE_API_BASE_URL` to the Render service origin before the build. It is baked into the static bundle. Do not set a trailing slash. After the frontend URL is known, set the backend `CORS_ORIGINS` to that origin and redeploy the API if the origin was not known on the first deploy.

Local `npm run dev` is unchanged and still uses the Vite proxy when `VITE_API_BASE_URL` is blank.
