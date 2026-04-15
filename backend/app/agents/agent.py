"""
TamilScholar Pro – LangGraph AI Agent
=====================================
A stateful multi-node scholarship discovery agent that:
  Node 1: Detects language and intent (Tamil/English/Tanglish)
  Node 2: Refines Tanglish queries into structured search params
  Node 3: Hybrid retrieval (SQL hard constraints + Pinecone semantic)
  Node 4: Contextual response in user's language with govt-grade empathy

Supports: Groq (Llama 3 70B) or OpenAI GPT-4o
"""
import json
import asyncio
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.services.scholarship_service import ScholarshipService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# AGENT STATE
# ─────────────────────────────────────────────────────────────────────────────
class Intent(str, Enum):
    SCHOLARSHIP_SEARCH = "scholarship_search"
    PROFILE_UPDATE = "profile_update"
    DEADLINE_QUERY = "deadline_query"
    DOCUMENT_SUMMARY = "document_summary"
    GENERAL_QUERY = "general_query"
    GREETING = "greeting"


class AgentState(TypedDict):
    """Full state passed between LangGraph nodes."""
    # Input
    user_message: str
    session_id: str
    user_profile: Optional[Dict[str, Any]]
    conversation_history: List[Dict[str, str]]
    db: Optional[Any]

    # Node 1 outputs
    detected_language: str          # "ta", "en", "tanglish"
    intent: Optional[Intent]
    intent_confidence: float

    # Node 2 outputs
    refined_query: Optional[str]
    structured_filters: Optional[Dict[str, Any]]  # income, community, gender, etc.

    # Node 3 outputs
    retrieved_scholarships: List[Dict[str, Any]]
    retrieval_metadata: Dict[str, Any]

    # Node 4 outputs
    final_response: Optional[str]
    response_language: str
    sources_used: List[str]

    # Error handling
    error: Optional[str]
    should_end: bool


# ─────────────────────────────────────────────────────────────────────────────
# LLM FACTORY
# ─────────────────────────────────────────────────────────────────────────────
def get_llm(temperature: Optional[float] = None):
    """Return the configured LLM (Groq or OpenAI)."""
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        # Avoid deprecated models by enforcing a current Groq model
        model = settings.LLM_MODEL
        if not model or model in {"mixtral-8x7b-32768", "llama-3.1-70b-versatile"}:
            model = "llama-3.3-70b-versatile"

        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=model,
            temperature=temp,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o",
            temperature=temp,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    else:
        raise RuntimeError("No LLM provider configured. Set GROQ_API_KEY or OPENAI_API_KEY.")


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: LANGUAGE & INTENT DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
async def node_detect_language_intent(state: AgentState) -> AgentState:
    """
    Detects:
    - Language: Tamil (ta), English (en), Tanglish (tanglish – Tamil written in English script)
    - Intent: What the user wants to do
    """
    llm = get_llm(temperature=0.1)

    system_prompt = """
    Analyze the user message and respond ONLY with a JSON object.
    The system is now English-centric.

    Respond ONLY with valid JSON. No markdown, no explanation.
    """



    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User message: {state['user_message']}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(raw)

        return {
            **state,
            "detected_language": parsed.get("language", "en"),
            "intent": Intent(parsed.get("intent", "general_query")),
            "intent_confidence": parsed.get("intent_confidence", 0.8),
            "structured_filters": parsed.get("key_entities", {}),
        }
    except Exception as e:
        logger.error(f"Node 1 error: {e}")
        return {
            **state,
            "detected_language": "en",
            "intent": Intent.GENERAL_QUERY,
            "intent_confidence": 0.5,
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: QUERY REFINER
# ─────────────────────────────────────────────────────────────────────────────
async def node_refine_query(state: AgentState) -> AgentState:
    """
    Converts Tanglish/Tamil/English into:
    1. A clean English semantic search query for Pinecone
    2. Structured SQL filters (income, community, gender, etc.)

    Also merges user profile data with entities detected in Node 1.
    """
    if state.get("intent") in [Intent.GREETING, Intent.GENERAL_QUERY]:
        return {
            **state,
            "refined_query": state["user_message"],
            "should_end": state.get("intent") == Intent.GREETING,
        }

    llm = get_llm(temperature=0.1)

    # Merge profile data with detected entities
    profile = state.get("user_profile", {}) or {}
    detected_entities = state.get("structured_filters", {}) or {}

    merged_profile = {
        "community": detected_entities.get("community") or profile.get("community"),
        "annual_income": detected_entities.get("income") or profile.get("annual_income"),
        "gender": detected_entities.get("gender") or profile.get("gender"),
        "course": detected_entities.get("course") or profile.get("course"),
        "grade_percentage": detected_entities.get("grade_percentage") or profile.get("grade_percentage"),
        "study_level": profile.get("study_level"),
        "state": profile.get("state", "Tamil Nadu"),
    }

    system_prompt = """You are a scholarship query refiner for the Tamil Nadu scholarship platform.
Always output a clear English refined query regardless of input language.

Common mappings:
- "scholarship venumda/vendum" -> "scholarship needed"
- "padikka" -> "to study"
- "panam" -> "money/financial assistance"

Respond ONLY with valid JSON."""

    user_context = f"""User message: {state['user_message']}
Known profile: {json.dumps(merged_profile, ensure_ascii=False)}
Detected entities: {json.dumps(detected_entities, ensure_ascii=False)}"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_context),
        ])
        raw = re.sub(r"```json|```", "", response.content.strip()).strip()
        parsed = json.loads(raw)

        # Deep merge SQL filters with profile
        sql_filters = parsed.get("sql_filters", {})
        if merged_profile["community"] and not sql_filters.get("category"):
            sql_filters["category"] = merged_profile["community"]
        if merged_profile["annual_income"] and not sql_filters.get("max_income"):
            sql_filters["max_income"] = float(merged_profile["annual_income"])

        return {
            **state,
            "refined_query": parsed.get("refined_query", state["user_message"]),
            "structured_filters": sql_filters,
        }
    except Exception as e:
        logger.error(f"Node 2 error: {e}")
        return {
            **state,
            "refined_query": state["user_message"],
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: HYBRID RETRIEVER
# ─────────────────────────────────────────────────────────────────────────────
async def node_hybrid_retriever(state: AgentState) -> AgentState:
    """
    Two-phase retrieval:
    Phase A: PostgreSQL hard-constraint filtering (income, community, gender)
    Phase B: Pinecone semantic search on the filtered set
    Merge and re-rank results by combined score.
    """
    if state.get("should_end"):
        return {**state, "retrieved_scholarships": []}

    try:
        embedding_svc = EmbeddingService()
        pinecone_svc = PineconeService()
        db_session = state.get("db")

        if not db_session:
            logger.warning("Node 3: Missing DB session; skipping SQL filter and returning empty scholarship list.")
            return {
                **state,
                "retrieved_scholarships": [],
                "retrieval_metadata": {
                    "sql_candidates_count": 0,
                    "semantic_results_count": 0,
                    "final_count": 0,
                    "filters_applied": state.get("structured_filters", {}),
                    "warning": "No database session provided",
                },
            }

        scholarship_svc = ScholarshipService(db=db_session)

        filters = state.get("structured_filters", {}) or {}
        query = state.get("refined_query", state["user_message"])

        # Phase A: SQL pre-filter
        sql_candidates = await scholarship_svc.filter_by_hard_constraints(
            category=filters.get("category"),
            max_income=filters.get("max_income"),
            gender_req=filters.get("gender_req"),
            course_type=filters.get("course_type"),
            study_level=filters.get("study_level"),
            min_percentage=filters.get("min_percentage"),
            limit=50,  # Get top 50 candidates for semantic re-ranking
        )

        if not sql_candidates:
            # Broaden search if no candidates
            sql_candidates = await scholarship_svc.filter_by_hard_constraints(limit=100)

        # Phase B: Semantic search on Pinecone
        query_embedding = await embedding_svc.embed_query(query)

        candidate_ids = [str(s["id"]) for s in sql_candidates]

        pinecone_results = await pinecone_svc.semantic_search(
            query_embedding=query_embedding,
            filter_ids=candidate_ids,
            top_k=10,
        )

        # Merge: combine SQL candidates with Pinecone scores
        scored_results = []
        pinecone_score_map = {r["scholarship_id"]: r["score"] for r in pinecone_results}

        for scholarship in sql_candidates:
            sid = str(scholarship["id"])
            semantic_score = pinecone_score_map.get(sid, 0.0)

            # Boost score if deadline is upcoming (urgency factor)
            urgency_boost = 0.0
            if scholarship.get("deadline"):
                from datetime import datetime, timezone
                days_left = (scholarship["deadline"] - datetime.now(timezone.utc)).days
                if 0 < days_left <= 30:
                    urgency_boost = 0.2
                elif 0 < days_left <= 60:
                    urgency_boost = 0.1

            scored_results.append({
                **scholarship,
                "semantic_score": semantic_score,
                "urgency_boost": urgency_boost,
                "final_score": semantic_score + urgency_boost,
            })

        # Sort by final score descending
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        top_results = scored_results[:8]  # Return top 8

        return {
            **state,
            "retrieved_scholarships": top_results,
            "retrieval_metadata": {
                "sql_candidates_count": len(sql_candidates),
                "semantic_results_count": len(pinecone_results),
                "final_count": len(top_results),
                "filters_applied": filters,
            },
        }

    except Exception as e:
        logger.error(f"Node 3 retrieval error: {e}")
        return {
            **state,
            "retrieved_scholarships": [],
            "retrieval_metadata": {"error": str(e)},
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3B: BEST-EFFORT RETRIEVER (vector rerank with hard timeouts)
# ─────────────────────────────────────────────────────────────────────────────
async def node_best_effort_retriever(state: AgentState) -> AgentState:
    """
    SQL-first retrieval, with an optional vector rerank attempt.

    If embeddings/Pinecone are slow or fail (e.g., HuggingFace download issues),
    we fall back to SQL-only results so the API never hangs.
    """
    if state.get("should_end"):
        return {**state, "retrieved_scholarships": []}

    db_session = state.get("db")
    if not db_session:
        logger.warning("Node 3B: Missing DB session; returning empty scholarship list.")
        return {
            **state,
            "retrieved_scholarships": [],
            "retrieval_metadata": {
                "sql_candidates_count": 0,
                "vector_attempted": False,
                "vector_used": False,
                "final_count": 0,
                "filters_applied": state.get("structured_filters", {}),
                "warning": "No database session provided",
            },
        }

    try:
        scholarship_svc = ScholarshipService(db=db_session)

        filters = state.get("structured_filters", {}) or {}
        query = state.get("refined_query", state["user_message"])

        # Phase A: SQL pre-filter (this should be fast)
        sql_candidates = await scholarship_svc.filter_by_hard_constraints(
            category=filters.get("category"),
            max_income=filters.get("max_income"),
            gender_req=filters.get("gender_req"),
            course_type=filters.get("course_type"),
            study_level=filters.get("study_level"),
            min_percentage=filters.get("min_percentage"),
            limit=50,
        )
        if not sql_candidates:
            sql_candidates = await scholarship_svc.filter_by_hard_constraints(limit=100)

        # Default ordering for SQL-only fallback.
        from datetime import datetime, timezone

        def deadline_ts(item: Dict[str, Any]) -> float:
            d = item.get("deadline")
            if not d:
                return float("inf")
            try:
                if isinstance(d, datetime):
                    return d.timestamp()
                return datetime.fromisoformat(str(d)).timestamp()
            except Exception:
                return float("inf")

        ordered_sql = sorted(sql_candidates, key=deadline_ts)
        sql_top = ordered_sql[:8]

        # Phase B: Best-effort vector rerank (bounded by timeouts)
        vector_embed_timeout_sec = 10
        vector_search_timeout_sec = 10
        vector_attempted = False
        vector_used = False

        try:
            embedding_svc = EmbeddingService()
            pinecone_svc = PineconeService()

            vector_attempted = True
            query_embedding = await asyncio.wait_for(
                embedding_svc.embed_query(query),
                timeout=vector_embed_timeout_sec,
            )

            candidate_ids = [str(s["id"]) for s in ordered_sql]
            pinecone_results = await asyncio.wait_for(
                pinecone_svc.semantic_search(
                    query_embedding=query_embedding,
                    filter_ids=candidate_ids,
                    top_k=10,
                ),
                timeout=vector_search_timeout_sec,
            )

            if pinecone_results:
                vector_used = True
                pinecone_score_map = {
                    r["scholarship_id"]: r["score"] for r in pinecone_results
                }

                scored_results = []
                for scholarship in ordered_sql:
                    sid = str(scholarship["id"])
                    semantic_score = pinecone_score_map.get(sid, 0.0)

                    # Boost score if deadline is upcoming (urgency factor)
                    urgency_boost = 0.0
                    if scholarship.get("deadline"):
                        days_left = int(
                            (scholarship["deadline"] - datetime.now(timezone.utc)).days
                        )
                        if 0 < days_left <= 30:
                            urgency_boost = 0.2
                        elif 0 < days_left <= 60:
                            urgency_boost = 0.1

                    scored_results.append(
                        {
                            **scholarship,
                            "semantic_score": semantic_score,
                            "urgency_boost": urgency_boost,
                            "final_score": semantic_score + urgency_boost,
                        }
                    )

                scored_results.sort(key=lambda x: x["final_score"], reverse=True)
                top_results = scored_results[:8]
                return {
                    **state,
                    "retrieved_scholarships": top_results,
                    "retrieval_metadata": {
                        "sql_candidates_count": len(sql_candidates),
                        "semantic_results_count": len(pinecone_results),
                        "final_count": len(top_results),
                        "filters_applied": filters,
                        "vector_attempted": True,
                        "vector_used": True,
                    },
                }

        except Exception as e:
            # Vector layer is optional; never fail the request due to it.
            logger.warning(f"Vector rerank skipped (best-effort): {e}")

        return {
            **state,
            "retrieved_scholarships": sql_top,
            "retrieval_metadata": {
                "sql_candidates_count": len(sql_candidates),
                "semantic_results_count": 0,
                "final_count": len(sql_top),
                "filters_applied": filters,
                "vector_attempted": vector_attempted,
                "vector_used": vector_used,
            },
        }

    except Exception as e:
        logger.error(f"Node 3B retrieval error: {e}")
        return {
            **state,
            "retrieved_scholarships": [],
            "retrieval_metadata": {"error": str(e)},
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4: CONTEXTUAL RESPONDER
# ─────────────────────────────────────────────────────────────────────────────
async def node_contextual_responder(state: AgentState) -> AgentState:
    """
    Generates a government-grade, empathetic response in the user's language.
    Includes scholarship details, application guidance, and deadline alerts.
    """
    llm = get_llm(temperature=0.4)

    lang = state.get("detected_language", "en")
    scholarships = state.get("retrieved_scholarships", [])
    intent = state.get("intent", Intent.GENERAL_QUERY)

    if intent == Intent.GREETING or state.get("should_end"):
        greeting_map = {
            "ta": "Welcome! We are ready to help you find the best scholarships in Tamil Nadu.",
            "tanglish": "Welcome! We are ready to help you find the best scholarships in Tamil Nadu.",
            "en": "Welcome to TamilScholar Pro! I'm your AI-powered scholarship guide for Tamil Nadu. Tell me about your community, income, and course – I'll find the best scholarships for you.",
        }
        return {
            **state,
            "final_response": greeting_map.get(lang, greeting_map["en"]),
            "response_language": "en",
            "sources_used": [],
        }

    # Format scholarships for prompt
    scholarship_text = ""
    sources = []
    for i, s in enumerate(scholarships[:6], 1):
        amount_str = f"₹{s['amount']:,.0f}/year" if s.get("amount") else "Amount varies"
        deadline_str = s["deadline"].strftime("%d %B %Y") if s.get("deadline") else "Rolling basis"
        scholarship_text += f"""
{i}. **{s['title']}**
   Provider: {s.get('provider', 'Tamil Nadu Government')}
   Category: {s.get('category', 'All')} | Amount: {amount_str}
   Deadline: {deadline_str}
   Apply: {s.get('application_url', 'https://scholarships.gov.in')}
"""
        sources.append(s.get("title", "Unknown"))

    # Always respond in English
    lang_instruction = "IMPORTANT: You MUST reply in clear, professional English only. Do not use Tamil script or Tanglish."

    system_prompt = f"""You are TamilScholar AI – an official AI assistant for the Tamil Nadu Government Scholarship Portal.

Your mission: Help students from Tamil Nadu discover and apply for government scholarships with CLARITY and EMPATHY.

Tone: Warm, encouraging, and trustworthy – like a knowledgeable government counselor who genuinely wants to help.

GUIDELINES:
1. Always address the student respectfully
2. Highlight urgency if a deadline is within 30 days
3. Mention required documents typically needed (income certificate, community certificate, marksheet)
4. If no scholarships match exactly, broaden the suggestion and explain why
5. Always end with an encouragement and next step
6. Never make up scholarship details – only use provided data
7. {lang_instruction}

Available scholarship data:
{scholarship_text if scholarship_text else "No specific scholarships found for these exact criteria."}

Conversation history context: {json.dumps(state.get('conversation_history', [])[-4:], ensure_ascii=False)}"""

    user_msg = f"""Student asked: "{state['user_message']}"
Student profile: {json.dumps(state.get('user_profile', {}), ensure_ascii=False)}
Detected intent: {intent}

Please provide a helpful, structured response with scholarship recommendations."""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])

        return {
            **state,
            "final_response": response.content,
            "response_language": lang,
            "sources_used": sources,
        }
    except Exception as e:
        logger.error(f"Node 4 error: {e}")
        error_messages = {
            "ta": "Apologies, we are experiencing a temporary service interruption. Please try again in a moment.",
            "tanglish": "Apologies, we are experiencing a temporary service interruption. Please try again in a moment.",
            "en": "We apologize for the inconvenience. Our service is temporarily unavailable. Please try again shortly.",
        }
        return {
            **state,
            "final_response": error_messages.get(lang, error_messages["en"]),
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def route_after_intent(state: AgentState) -> str:
    """Route based on detected intent."""
    intent = state.get("intent")
    if intent in [Intent.GREETING]:
        return "respond"  # Skip retrieval for greetings
    if intent == Intent.PROFILE_UPDATE:
        return "refine"   # Update profile, then search
    return "refine"       # Default: refine → retrieve → respond


def route_after_refine(state: AgentState) -> str:
    """After query refinement, decide next step."""
    if state.get("should_end"):
        return "respond"
    return "retrieve"


# ─────────────────────────────────────────────────────────────────────────────
# BUILD LANGGRAPH
# ─────────────────────────────────────────────────────────────────────────────
def build_scholarship_agent() -> StateGraph:
    """Compile the LangGraph scholarship agent."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("detect", node_detect_language_intent)
    graph.add_node("refine", node_refine_query)
    graph.add_node("retrieve", node_hybrid_retriever)
    graph.add_node("respond", node_contextual_responder)

    # Set entry point
    graph.set_entry_point("detect")

    # Add edges
    graph.add_conditional_edges("detect", route_after_intent, {
        "refine": "refine",
        "respond": "respond",
    })
    graph.add_conditional_edges("refine", route_after_refine, {
        "retrieve": "retrieve",
        "respond": "respond",
    })
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


# Singleton agent instance
scholarship_agent = build_scholarship_agent()


def build_scholarship_agent_v2() -> StateGraph:
    """
    Agent v2: same language + query refinement, but retrieval is best-effort.

    Vector reranking is optional and time-bounded, so the API doesn't hang when
    embeddings/Pinecone are unavailable.
    """
    graph = StateGraph(AgentState)

    graph.add_node("detect", node_detect_language_intent)
    graph.add_node("refine", node_refine_query)
    graph.add_node("retrieve", node_best_effort_retriever)
    graph.add_node("respond", node_contextual_responder)

    graph.set_entry_point("detect")

    graph.add_conditional_edges(
        "detect",
        route_after_intent,
        {
            "refine": "refine",
            "respond": "respond",
        },
    )
    graph.add_conditional_edges(
        "refine",
        route_after_refine,
        {
            "retrieve": "retrieve",
            "respond": "respond",
        },
    )
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


# Singleton agent instance (v2)
scholarship_agent_v2 = build_scholarship_agent_v2()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────
async def run_scholarship_agent(
    user_message: str,
    session_id: str,
    user_profile: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Main entry point for the scholarship agent.
    Returns the agent's response with metadata.
    """
    initial_state: AgentState = {
        "user_message": user_message,
        "session_id": session_id,
        "user_profile": user_profile or {},
        "conversation_history": conversation_history or [],
        "detected_language": "en",
        "db": db,
        "intent": None,
        "intent_confidence": 0.0,
        "refined_query": None,
        "structured_filters": {},
        "retrieved_scholarships": [],
        "retrieval_metadata": {},
        "final_response": None,
        "response_language": "en",
        "sources_used": [],
        "error": None,
        "should_end": False,
    }

    try:
        final_state = await scholarship_agent.ainvoke(initial_state)
        return {
            "response": final_state.get("final_response", "I couldn't process your request."),
            "language": final_state.get("response_language", "en"),
            "intent": final_state.get("intent", Intent.GENERAL_QUERY),
            "scholarships": final_state.get("retrieved_scholarships", [])[:6],
            "sources": final_state.get("sources_used", []),
            "extra_metadata": {
                "retrieval": final_state.get("retrieval_metadata", {}),
                "filters_applied": final_state.get("structured_filters", {}),
                "detected_language": final_state.get("detected_language"),
            },
            "error": final_state.get("error"),
        }
    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        return {
            "response": "We're experiencing technical difficulties. Please try again.",
            "language": "en",
            "error": str(e),
            "scholarships": [],
        }


async def run_scholarship_agent_v2(
    user_message: str,
    session_id: str,
    user_profile: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Agent v2 entry point. Same contract as `run_scholarship_agent`, but uses
    best-effort retrieval to prevent timeouts.
    """
    initial_state: AgentState = {
        "user_message": user_message,
        "session_id": session_id,
        "user_profile": user_profile or {},
        "conversation_history": conversation_history or [],
        "detected_language": "en",
        "db": db,
        "intent": None,
        "intent_confidence": 0.0,
        "refined_query": None,
        "structured_filters": {},
        "retrieved_scholarships": [],
        "retrieval_metadata": {},
        "final_response": None,
        "response_language": "en",
        "sources_used": [],
        "error": None,
        "should_end": False,
    }

    try:
        final_state = await scholarship_agent_v2.ainvoke(initial_state)
        return {
            "response": final_state.get("final_response", "I couldn't process your request."),
            "language": final_state.get("response_language", "en"),
            "intent": final_state.get("intent", Intent.GENERAL_QUERY),
            "scholarships": final_state.get("retrieved_scholarships", [])[:6],
            "sources": final_state.get("sources_used", []),
            "extra_metadata": {
                "retrieval": final_state.get("retrieval_metadata", {}),
                "filters_applied": final_state.get("structured_filters", {}),
                "detected_language": final_state.get("detected_language"),
            },
            "error": final_state.get("error"),
        }
    except Exception as e:
        logger.exception(f"Agent v2 execution failed: {e}")
        return {
            "response": "We're experiencing technical difficulties. Please try again.",
            "language": "en",
            "error": str(e),
            "scholarships": [],
        }
