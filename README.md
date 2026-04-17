# TamilScholar Pro 🎓
### AI-Powered Multilingual Scholarship Engine for Tamil Nadu

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-blue)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com)

---

## 🌟 Features

### Core AI & Search
- **Multilingual AI Chat** – Tamil, Tanglish (Tamil in English script), and English
- **LangGraph Agent** – 4-node stateful pipeline with language detection, query refinement, hybrid retrieval, and contextual response
- **Hybrid Search** – PostgreSQL hard-constraint filtering + Pinecone semantic vector search
- **BGE-M3 Embeddings** – 1024-dim multilingual embeddings for accurate Tamil/English cross-lingual retrieval
- **Groq Inference** – Ultra-fast Llama 3 70B responses via Groq API
- **Streaming Responses** – Real-time token streaming for chat interface
- **Reranking Support** – Cohere Rerank integration for improved retrieval precision

### Security & Auth
- **RS256 JWT Auth** – Secure asymmetric token signing with rotation
- **OAuth 2.0** – Google SSO integration
- **CSRF Protection** – Cross-site request forgery protection
- **Prompt Guard** – Jailbreak detection middleware
- **Rate Limiting** – SlowAPI per-IP throttling
- **Security Headers** – HSTS, CSP, X-Frame-Options, etc.

### Performance & Scalability
- **Redis Caching** – Query, session, and embedding caching
- **Celery + RabbitMQ** – Async task queue for background jobs
- **Connection Pooling** – PgBouncer-ready PostgreSQL pooling
- **Response Caching** – Intelligent cache invalidation

### Monitoring & Observability
- **Sentry Integration** – Error tracking and performance monitoring
- **Structured Logging** – JSON logs with structlog for production
- **Health Checks** – Dependency health monitoring (Redis, DB, Pinecone)
- **APM Ready** – Performance profiling enabled

### Frontend Features
- **Dark Mode** – System-aware dark theme support
- **PWA Support** – Offline capabilities with service workers
- **Responsive Design** – Mobile-first approach
- **Accessibility** – WCAG 2.1 AA compliant

### Data
- **10 Real Scholarships** – Pre-seeded with actual Tamil Nadu government schemes (BC, MBC, SC, ST, General, OBC, EWS, Minority)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                   │
│  React Query · next-intl · Tailwind · Dark Mode · PWA   │
└─────────────────┬───────────────────────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend                         │
│  Sentry │ CSRF │ Rate Limiting │ RS256 JWT │ OAuth 2.0   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │              LangGraph Agent                     │    │
│  │  Node 1: Language & Intent Detection            │    │
│  │  Node 2: Query Refinement (Tanglish → English)  │    │
│  │  Node 3: Hybrid Retrieval (SQL + Pinecone)      │    │
│  │  Node 4: Contextual Response Generator          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Celery Workers                     │    │
│  │  Embedding Tasks · Notification Tasks            │    │
│  │  PDF Processing · Data Ingestion                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  PostgreSQL + pgvector    Pinecone Serverless            │
│  (Hard-constraint filter) (Semantic similarity)          │
│                                                           │
│  Redis (Caching)          RabbitMQ (Message Queue)       │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Docker)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/tamilscholar-pro.git
cd tamilscholar-pro

# 2. Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys:
#   GROQ_API_KEY=gsk_...
#   PINECONE_API_KEY=...

# 3. Start all services
docker compose up -d

# 4. Seed demo data (real Tamil Nadu scholarships)
docker exec tamilscholar_backend python /app/scripts/ingest_scholarships.py --seed-demo

# 5. Open the app
open http://localhost:3000
```

---

## 🔑 API Keys Required

| Service | Get Key | Used For |
|---------|---------|---------|
| **Groq** | [console.groq.com](https://console.groq.com) | Llama 3 70B inference (free tier available) |
| **Pinecone** | [app.pinecone.io](https://app.pinecone.io) | Vector similarity search (free serverless) |
| **Google OAuth** | [console.cloud.google.com](https://console.cloud.google.com) | Google SSO authentication |
| **Sentry** | [sentry.io](https://sentry.io) | Error tracking and monitoring (optional) |

Optional:
| **OpenAI** | [platform.openai.com](https://platform.openai.com) | GPT-4o (alternative to Groq) |
| **Cohere** | [cohere.com](https://cohere.com) | Reranking model (optional) |

---

## 📁 Project Structure

```
tamilscholar-pro/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── agents/
│   │   │   └── agent.py         # LangGraph 4-node agent
│   │   ├── api/v1/endpoints/
│   │   │   ├── auth.py          # JWT + OAuth endpoints
│   │   │   ├── chat.py          # AI chat + streaming
│   │   │   ├── scholarships.py  # Search & CRUD
│   │   │   ├── admin.py         # Admin management
│   │   │   └── reminders.py     # Deadline reminders
│   │   ├── models/models.py     # SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── auth_service.py      # RS256 JWT + bcrypt
│   │   │   ├── scholarship_service.py # Hybrid search
│   │   │   ├── embedding_service.py  # BGE-M3 wrapper
│   │   │   ├── pinecone_service.py   # Vector DB ops
│   │   │   ├── redis_service.py      # Redis caching
│   │   │   ├── oauth_service.py      # Google OAuth
│   │   │   └── ingestion_service.py  # PDF → chunks → embeddings
│   │   ├── tasks/
│   │   │   ├── celery_app.py         # Celery configuration
│   │   │   ├── embedding_tasks.py    # Async embedding jobs
│   │   │   ├── notification_tasks.py # Email/SMS notifications
│   │   │   └── ingestion_tasks.py    # Async data ingestion
│   │   ├── middleware/
│   │   │   ├── prompt_guard.py  # Jailbreak detection
│   │   │   ├── security.py      # Security headers
│   │   │   └── csrf.py          # CSRF protection
│   │   └── utils/
│   │       └── logging_config.py # Structured logging
│   ├── tests/
│   │   └── test_api.py         # Integration tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx       # Root layout with ThemeProvider
│       │   ├── page.tsx         # Homepage
│       │   ├── chat/page.tsx    # AI Chat interface
│       │   ├── scholarships/    # Scholarship listing
│       │   └── admin/           # Admin dashboard
│       ├── components/
│       │   ├── scholarship/     # ScholarshipCard, MiniCard
│       │   ├── providers/       # QueryProvider, ThemeProvider
│       │   └── ui/              # UI components
│       ├── hooks/               # useChat, useScholarships, useAdmin
│       └── lib/api.ts           # Axios API client
├── .github/workflows/
│   └── ci-cd.yml               # CI/CD pipeline
├── scripts/
│   └── ingest_scholarships.py   # Data ingestion + demo seeder
└── docker-compose.yml           # All services (Postgres, Redis, RabbitMQ, etc.)
```

---

## 🌐 Deployment

### Quick Local Deployment (Docker Compose)

```bash
# 1. Clone and navigate to project
cd tamilscholar-pro/tamilscholar-pro

# 2. Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 3. Start all services
docker compose up -d

# 4. Seed demo data
docker exec tamilscholar_backend python /app/scripts/ingest_scholarships.py --seed-demo

# 5. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Health Check: http://localhost:8000/health
# RabbitMQ Management: http://localhost:15672 (guest/guest)
```

### Production Deployment Options

#### Option 1: Render + Supabase (Recommended - Best Free Tier)

**Note: Railway has storage limits. Render + Supabase provides better free tier storage.**

1. **Backend on Render**
   - Create a new **Web Service** on [render.com](https://render.com)
   - Root directory: `tamilscholar-pro/backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add all environment variables from `.env.example`

2. **Supabase for Database & Redis** (Free tier: 500MB PostgreSQL + Redis)
   - Create account at [supabase.com](https://supabase.com)
   - Create a new project
   - Enable pgvector extension in SQL editor: `CREATE EXTENSION vector;`
   - Get connection string from Settings > Database
   - Use Supabase's built-in Redis or add Redis from Render marketplace
   - Add RabbitMQ from Render marketplace (or use Supabase Edge Functions for async tasks)

3. **Frontend on Vercel**
   ```bash
   cd tamilscholar-pro/frontend
   npx vercel --prod
   ```
   - Set `NEXT_PUBLIC_API_URL` to your Render backend URL
   - Add environment variables for OAuth

#### Option 2: Fly.io + Neon (Alternative Free Tier)

1. **Backend on Fly.io**
   - Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
   - Create account at [fly.io](https://fly.io)
   - Deploy: `cd tamilscholar-pro/backend && fly launch`
   - Add volumes for persistent storage
   - Add environment variables

2. **Neon PostgreSQL** (Free tier: 0.5GB with pgvector)
   - Create account at [neon.tech](https://neon.tech)
   - Create project with pgvector enabled
   - Use connection string in Fly.io environment

3. **Upstash Redis** (Free tier: 10,000 commands/day)
   - Create account at [upstash.com](https://upstash.com)
   - Create Redis database
   - Use connection string in Fly.io environment

4. **Frontend on Vercel** (same as above)

#### Option 3: AWS Free Tier (12 Months Free - Requires Credit Card)

1. **AWS ECS + RDS PostgreSQL + ElastiCache**
   - Create AWS account (12 months free tier eligible)
   - RDS PostgreSQL with pgvector (750 hours/month free)
   - ElastiCache Redis (750 hours/month free)
   - Deploy backend to ECS Fargate
   - Deploy frontend to Amplify or CloudFront + S3

#### Option 4: Self-Hosted (VPS - Full Control)

**Recommended VPS Providers:**
- **DigitalOcean** - $4/month (1GB RAM, 25GB SSD)
- **Linode** - $5/month (1GB RAM, 25GB SSD)
- **Hetzner** - €4/month (2GB RAM, 40GB SSD) - Best value

**Deployment Steps:**
```bash
# On your VPS:
# 1. Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Clone repository
git clone https://github.com/your-org/tamilscholar-pro.git
cd tamilscholar-pro/tamilscholar-pro

# 3. Set environment variables
cp backend/.env.example backend/.env
nano backend/.env  # Add your API keys

# 4. Start services
docker compose up -d

# 5. Configure reverse proxy (Nginx)
# 6. Add SSL certificate (Let's Encrypt)
# 7. Point domain to VPS IP
```

#### Option 5: AWS ECS (Enterprise)

```bash
# Build and push Docker images
docker build -t tamilscholar-backend ./backend
docker build -t tamilscholar-frontend ./frontend

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/tamilscholar-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/tamilscholar-frontend:latest

# Deploy to ECS with Fargate
# Use RDS PostgreSQL with pgvector
# Use ElastiCache for Redis
# Use MQ for RabbitMQ
```

### Environment Variables

Required environment variables (see `backend/.env.example`):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0

# RabbitMQ
CELERY_BROKER_URL=amqp://user:pass@host:5672/
CELERY_RESULT_BACKEND=redis://host:6379/1

# AI Services
GROQ_API_KEY=gsk_...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=tamilscholar-scholarships

# OAuth (Optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback/google

# Sentry (Optional)
SENTRY_DSN=https://...

# Security
SECRET_KEY=use-openssl-rand-hex-64
ENVIRONMENT=production
```

---

## 🤖 AI Agent Details

The LangGraph agent processes each message through 4 nodes:

**Node 1 – Language & Intent Detection**
- Detects: Tamil (ta), English (en), Tanglish
- Classifies intent: scholarship_search, profile_update, deadline_query, greeting, general_query

**Node 2 – Query Refinement**
- Converts Tanglish to structured English queries
- Extracts: community, income, gender, course, grade
- Merges with user profile data

**Node 3 – Hybrid Retrieval**
- Phase A: PostgreSQL filters by income, community, gender (hard constraints)
- Phase B: Pinecone semantic search on filtered candidates
- Scoring: semantic_score + urgency_boost (deadline proximity)

**Node 4 – Contextual Response**
- Generates response in detected language
- System prompt: "Government-grade clarity and empathy"
- Includes scholarship cards, application URLs, deadline warnings

---

## 📊 Demo Scholarships (Pre-seeded)

| Scholarship | Category | Amount |
|------------|----------|--------|
| Chief Minister's Special Scholarship | BC | ₹50,000/yr |
| Moovalur Ramamirtham Ammaiyar | MBC | ₹12,000/yr |
| Post-Matric Scholarship SC/ST | SC | ₹83,000/yr |
| Free Education Scheme ST | ST | ₹1,00,000/yr |
| EWS Higher Education | EWS | ₹25,000/yr |
| National Scholarship Portal | General | ₹20,000/yr |
| Tamil Nadu Minority Scholarship | Minority | ₹30,000/yr |
| OBC Pre-Matric | OBC | ₹5,000/yr |
| Dr. Ambedkar Law Scholarship | SC | ₹25,000/yr |
| Anaithu Grama Girl Scholarship | MBC | ₹15,000/yr |

---

## 📄 License

Government Open Data License – Tamil Nadu Government Initiative
