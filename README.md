# ClaimProof

**72 Hours to Prove Your Loss.** — AgriTech · AI-assisted evidence preparation

> **Hackathon MVP — not production-ready.**

## What is ClaimProof?

A mobile-first web app that helps insured farmers prepare crop-loss evidence within the PMFBY 72-hour intimation window. It does **not** submit claims or replace official channels.

## Architecture

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS, TanStack Query |
| Backend | Python 3.12, FastAPI, Pydantic v2, ReportLab |
| Database | Supabase (PostgreSQL + Auth + Storage) |
| AI | Google Gemini Vision (advisory, fail-soft) |
| Weather | Open-Meteo (context only, CC BY 4.0) |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ with npm
- A Supabase project

### Backend

```bash
cd backend
cp .env.example .env   # fill in your values
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local   # fill in your values
npm ci
npm run dev
```

### Database

Run `supabase/migrations/0001_init.sql` in your Supabase SQL editor.

## Documentation

See [SPEC.md](SPEC.md) for the full product and technical specification.

## Disclaimer

ClaimProof is **not** an official insurer or government service. It prepares supplementary evidence for the farmer's own use. Always inform your insurer through official channels (Crop Insurance App, helpline 14447, insurer, bank, or agriculture department).
