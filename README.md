# TamilScholar Pro 🎓
### AI-Powered Multilingual Scholarship Engine for Tamil Nadu

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-blue)](https://langchain-ai.github.io/langgraph/)

---

## 🌟 Features

- **Multilingual AI Chat** – Tamil, Tanglish (Tamil in English script), and English
- **LangGraph Agent** – 4-node stateful pipeline with language detection, query refinement, hybrid retrieval, and contextual response
- **Hybrid Search** – PostgreSQL hard-constraint filtering + Pinecone semantic vector search
- **BGE-M3 Embeddings** – 1024-dim multilingual embeddings for accurate Tamil/English cross-lingual retrieval
- **Groq Inference** – Ultra-fast Llama 3 70B responses via Groq API
- **Prompt Guard** – Jailbreak detection middleware
- **Rate Limiting** – SlowAPI per-IP throttling
- **RS256 JWT Auth** – Secure asymmetric token signing with rotation
- **10 Real Scholarships** – Pre-seeded with actual Tamil Nadu government schemes (BC, MBC, SC, ST, General, OBC, EWS, Minority)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                   │
│          React Query · next-intl · Tailwind CSS          │
└─────────────────┬───────────────────────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend                         │
│    Prompt Guard │ Rate Limiting │ RS256 JWT              │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │              LangGraph Agent                     │    │
│  │  Node 1: Language & Intent Detection            │    │
│  │  Node 2: Query Refinement (Tanglish → English)  │    │
│  │  Node 3: Hybrid Retrieval (SQL + Pinecone)      │    │
│  │  Node 4: Contextual Response Generator          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  PostgreSQL + pgvector    Pinecone Serverless            │
│  (Hard-constraint filter) (Semantic similarity)          │
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

Optional:
| **OpenAI** | [platform.openai.com](https://platform.openai.com) | GPT-4o (alternative to Groq) |

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
│   │   │   ├── auth.py          # JWT auth endpoints
│   │   │   ├── chat.py          # AI chat endpoints
│   │   │   ├── scholarships.py  # Search & CRUD
│   │   │   ├── admin.py         # Admin management
│   │   │   └── reminders.py     # Deadline reminders
│   │   ├── models/models.py     # SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── auth_service.py      # RS256 JWT + bcrypt
│   │   │   ├── scholarship_service.py # Hybrid search
│   │   │   ├── embedding_service.py  # BGE-M3 wrapper
│   │   │   ├── pinecone_service.py   # Vector DB ops
│   │   │   └── ingestion_service.py  # PDF → chunks → embeddings
│   │   └── middleware/
│   │       ├── prompt_guard.py  # Jailbreak detection
│   │       └── security.py      # Security headers
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Homepage
│       │   ├── chat/page.tsx    # AI Chat interface
│       │   ├── scholarships/    # Scholarship listing
│       │   └── admin/           # Admin dashboard
│       ├── components/
│       │   ├── scholarship/     # ScholarshipCard, MiniCard
│       │   └── providers/       # React Query provider
│       ├── hooks/               # useChat, useScholarships, useAdmin
│       └── lib/api.ts           # Axios API client
├── scripts/
│   └── ingest_scholarships.py   # Data ingestion + demo seeder
└── docker-compose.yml
```

---

## 🌐 Deployment

### Vercel (Frontend)

```bash
cd frontend
npx vercel --prod
# Set env vars in Vercel dashboard:
#   NEXT_PUBLIC_API_URL=https://your-backend.render.com
```

### Render (Backend)

1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect your repository
3. Set build directory to `backend/`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables from `backend/.env.example`

### AWS (Full Stack)

```bash
# Build and push Docker images
docker build -t tamilscholar-backend ./backend
docker build -t tamilscholar-frontend ./frontend

# Deploy to ECS or EC2
# RDS PostgreSQL with pgvector: use pgvector/pgvector:pg16 AMI
# ElastiCache Redis for rate limiting
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
