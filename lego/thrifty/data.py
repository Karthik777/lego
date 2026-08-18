"""The platform catalogue and the use-case templates the calculator is built from.

Ported from thrifty's `platforms.py`. `get_recommendations` did not come with it: it is
server-side dead code — the page computes the same thing in the browser from the
`scale_fit`/`complexity_fit` lists that `page_data` serialises. Nor did `models.py`, whose
job the client does by fetching LiteLLM and OpenRouter pricing directly.
"""
import json
from functools import cache
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

class ScaleCategory(Enum):
    STARTUP = "startup"  # < 100K requests/month
    GROWTH = "growth"    # 100K - 1M requests/month
    SCALE = "scale"      # 1M - 10M requests/month
    ENTERPRISE = "enterprise"  # 10M+ requests/month

class ComplexityLevel(Enum):
    LOW = "low"       # Simple prompt/response
    MEDIUM = "medium" # Multi-step, some context
    HIGH = "high"     # Complex agents, tool use, long context

@dataclass
class PlatformOption:
    name: str
    category: str
    description: str
    pros: List[str]
    cons: List[str]
    pricing_model: str
    estimated_monthly_base: float  # Base cost $/month
    estimated_per_request: float   # Additional $/request (platform overhead, not LLM)
    best_for: List[str]
    scale_fit: List[ScaleCategory]
    complexity_fit: List[ComplexityLevel]
    url: str = ""

# LLM/Agent Framework Approaches
AGENT_FRAMEWORKS = {
    "openai_agents": PlatformOption(
        name="OpenAI Agents SDK",
        category="agent_framework",
        description="Official OpenAI SDK for building agentic applications with tool use, handoffs, and guardrails",
        pros=["Official OpenAI support", "Native tool calling", "Built-in tracing", "Handoff patterns", "Guardrails included"],
        cons=["OpenAI-specific", "Newer ecosystem", "Limited to OpenAI models"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["OpenAI-based agents", "Production agent systems", "Tool-heavy workflows"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://github.com/openai/openai-agents-python"
    ),
    "lisette": PlatformOption(
        name="Lisette",
        category="agent_framework",
        description="Minimal, elegant agent framework from Answer.AI focused on simplicity and composability",
        pros=["Minimal abstraction", "Clean API", "Composable design", "Fast iteration", "Lightweight"],
        cons=["Newer framework", "Smaller community", "Less batteries-included"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Rapid prototyping", "Simple agents", "Composable workflows", "Learning agent patterns"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://github.com/AnswerDotAI/lisette"
    ),
    "pydantic_ai": PlatformOption(
        name="Pydantic AI",
        category="agent_framework",
        description="Type-safe agent framework built on Pydantic with structured outputs and validation",
        pros=["Type safety", "Structured outputs", "Model agnostic", "Great DX", "Validation built-in"],
        cons=["Requires Pydantic knowledge", "Newer framework"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Type-safe applications", "Structured data extraction", "Production systems"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://ai.pydantic.dev"
    ),
    "langchain": PlatformOption(
        name="LangChain",
        category="agent_framework",
        description="Comprehensive framework for building LLM applications with chains, agents, and tools",
        pros=["Large ecosystem", "Extensive integrations", "Good documentation", "Active community"],
        cons=["Can be complex", "Abstraction overhead", "Frequent breaking changes", "Over-engineered for simple cases"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Complex integrations", "RAG applications", "When you need specific integrations"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://langchain.com"
    ),
    "llamaindex": PlatformOption(
        name="LlamaIndex",
        category="agent_framework",
        description="Data framework for LLM applications, specialized in RAG and data ingestion",
        pros=["Excellent for RAG", "Strong data connectors", "Good indexing strategies", "Workflow engine"],
        cons=["Less flexible for non-RAG use cases", "Steeper learning curve"],
        pricing_model="Open source (free) / LlamaCloud for managed",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["RAG applications", "Document Q&A", "Knowledge bases"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://llamaindex.ai"
    ),
    "smolagents": PlatformOption(
        name="smolagents (Hugging Face)",
        category="agent_framework",
        description="Hugging Face's lightweight agent library focused on code-based agents",
        pros=["Code agents", "HF ecosystem", "Lightweight", "Good for research"],
        cons=["Less production-focused", "Smaller community"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Code-based agents", "Research", "HF model integration"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://github.com/huggingface/smolagents"
    ),
    "anthropic_claude": PlatformOption(
        name="Anthropic Claude SDK",
        category="agent_framework",
        description="Direct Claude API with tool use, computer use, and extended thinking capabilities",
        pros=["Native Claude features", "Computer use", "Extended thinking", "Best Claude performance"],
        cons=["Anthropic-only", "Manual orchestration needed"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Claude-based apps", "Computer use agents", "Complex reasoning"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://docs.anthropic.com/en/docs/agents-and-tools"
    ),
    "direct_api": PlatformOption(
        name="Direct API Calls",
        category="agent_framework",
        description="Direct integration with LLM provider APIs without frameworks",
        pros=["Full control", "No abstraction overhead", "Minimal dependencies", "Best performance"],
        cons=["More code to maintain", "No built-in patterns", "Build everything yourself"],
        pricing_model="Free (just LLM costs)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Simple use cases", "Performance-critical apps", "Custom implementations"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM],
        url=""
    ),
}

# Vector Store / Data Store Patterns
VECTOR_STORES = {
    "pinecone": PlatformOption(
        name="Pinecone",
        category="vector_store",
        description="Fully managed vector database optimized for ML embeddings",
        pros=["Fully managed", "Fast queries", "Good scaling", "Hybrid search"],
        cons=["Can get expensive at scale", "Vendor lock-in", "Limited filtering"],
        pricing_model="Free tier + usage-based ($0.096/hr for pods)",
        estimated_monthly_base=70,
        estimated_per_request=0.000001,
        best_for=["Production RAG", "Semantic search", "Recommendation systems"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://pinecone.io"
    ),
    "weaviate": PlatformOption(
        name="Weaviate",
        category="vector_store",
        description="Open-source vector database with built-in ML models",
        pros=["Open source option", "Built-in vectorization", "GraphQL API", "Hybrid search"],
        cons=["Self-hosting complexity", "Resource intensive"],
        pricing_model="Open source / Weaviate Cloud from $25/mo",
        estimated_monthly_base=25,
        estimated_per_request=0.0000005,
        best_for=["Self-hosted deployments", "Complex queries", "Multi-modal search"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://weaviate.io"
    ),
    "qdrant": PlatformOption(
        name="Qdrant",
        category="vector_store",
        description="High-performance vector similarity search engine",
        pros=["Excellent performance", "Rich filtering", "Open source", "Rust-based efficiency"],
        cons=["Smaller ecosystem", "Less enterprise support"],
        pricing_model="Open source / Cloud from $25/mo",
        estimated_monthly_base=25,
        estimated_per_request=0.0000003,
        best_for=["High-performance search", "Complex filtering needs", "Cost-conscious teams"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://qdrant.tech"
    ),
    "chromadb": PlatformOption(
        name="ChromaDB",
        category="vector_store",
        description="Simple, developer-friendly embedding database",
        pros=["Very easy to use", "Great for prototyping", "Open source", "In-memory option"],
        cons=["Limited scale", "Basic features", "Not for production at scale"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Prototyping", "Small-scale RAG", "Local development"],
        scale_fit=[ScaleCategory.STARTUP],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM],
        url="https://trychroma.com"
    ),
    "pgvector": PlatformOption(
        name="pgvector (PostgreSQL)",
        category="vector_store",
        description="Vector similarity search extension for PostgreSQL",
        pros=["Use existing Postgres", "SQL interface", "ACID compliance", "Cost effective"],
        cons=["Performance limits at scale", "Manual optimization needed"],
        pricing_model="Free (just Postgres hosting costs)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Existing Postgres users", "Hybrid data needs", "Cost optimization"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM],
        url="https://github.com/pgvector/pgvector"
    ),
    "litesearch": PlatformOption(
        name="LiteSearch",
        category="vector_store",
        description="SQLite FTS5 + vector search for lightweight RAG applications",
        pros=["Zero infrastructure", "FTS5 full-text search", "Hybrid search", "Serverless-friendly", "Single file DB"],
        cons=["SQLite limitations at scale", "Single-writer"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Serverless RAG", "Edge deployments", "Simple applications", "Prototyping"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM],
        url="https://github.com/Karthik777/litesearch"
    ),
    "lancedb": PlatformOption(
        name="LanceDB",
        category="vector_store",
        description="Serverless vector database built on Lance columnar format",
        pros=["Serverless", "No infrastructure", "Fast", "Multi-modal", "Open source"],
        cons=["Newer project", "Smaller community"],
        pricing_model="Open source (free) / Cloud available",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Serverless apps", "Multi-modal search", "Edge deployments"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://lancedb.com"
    ),
}

# CI/CD Approaches for LLM Applications
CICD_APPROACHES = {
    "github_actions": PlatformOption(
        name="GitHub Actions",
        category="cicd",
        description="GitHub's native CI/CD with LLM testing integrations",
        pros=["Native GitHub integration", "Large marketplace", "Easy secrets management"],
        cons=["Limited free minutes", "YAML complexity", "GitHub dependency"],
        pricing_model="Free tier (2000 min/mo) + $0.008/min",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["GitHub-hosted projects", "Standard CI/CD needs", "Open source projects"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://github.com/features/actions"
    ),
    "gitlab_cicd": PlatformOption(
        name="GitLab CI/CD",
        category="cicd",
        description="GitLab's integrated CI/CD pipeline system",
        pros=["All-in-one platform", "Self-hosting option", "Good security features"],
        cons=["Can be complex", "Resource intensive self-hosting"],
        pricing_model="Free tier + $29/user/mo for Premium",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["GitLab users", "Enterprise security needs", "Self-hosted requirements"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://docs.gitlab.com/ee/ci/"
    ),
    "azure_devops": PlatformOption(
        name="Azure DevOps",
        category="cicd",
        description="Microsoft's DevOps platform with Azure AI integration",
        pros=["Azure integration", "Enterprise features", "Good for .NET"],
        cons=["Complex pricing", "Microsoft ecosystem focus"],
        pricing_model="Free tier (1800 min/mo) + usage",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Azure-centric orgs", "Enterprise compliance", "Windows/.NET projects"],
        scale_fit=[ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://azure.microsoft.com/en-us/products/devops"
    ),
}

# Observability and Evaluation Approaches
OBSERVABILITY_TOOLS = {
    "langsmith": PlatformOption(
        name="LangSmith",
        category="observability",
        description="LangChain's tracing and evaluation platform",
        pros=["Deep LangChain integration", "Good tracing", "Evaluation datasets", "Prompt versioning"],
        cons=["LangChain-focused", "Can get expensive", "Limited non-LangChain support"],
        pricing_model="Free tier (5K traces) + $39/seat/mo",
        estimated_monthly_base=39,
        estimated_per_request=0.00001,
        best_for=["LangChain users", "Prompt debugging", "Evaluation workflows"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://smith.langchain.com"
    ),
    "langfuse": PlatformOption(
        name="Langfuse",
        category="observability",
        description="Open-source LLM observability and analytics",
        pros=["Open source", "Framework agnostic", "Good analytics", "Self-host option"],
        cons=["Smaller ecosystem", "Less polished UI", "Manual setup"],
        pricing_model="Open source / Cloud from $59/mo",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Cost-conscious teams", "Multi-framework setups", "Self-hosting needs"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://langfuse.com"
    ),
    "arize_phoenix": PlatformOption(
        name="Arize Phoenix",
        category="observability",
        description="Open-source LLM observability with eval focus",
        pros=["Open source", "Strong eval features", "Good visualizations", "Drift detection"],
        cons=["Complex setup", "Resource intensive"],
        pricing_model="Open source (free)",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["ML teams", "Evaluation-heavy workflows", "Production monitoring"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://phoenix.arize.com"
    ),
    "helicone": PlatformOption(
        name="Helicone",
        category="observability",
        description="LLM observability platform with cost tracking",
        pros=["Easy integration", "Cost analytics", "Good dashboards", "Caching features"],
        cons=["Proxy-based (adds latency)", "Limited eval features"],
        pricing_model="Free tier (100K req) + $20/mo",
        estimated_monthly_base=20,
        estimated_per_request=0.000005,
        best_for=["Cost optimization", "Quick setup", "Request caching"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM],
        url="https://helicone.ai"
    ),
    "weights_biases": PlatformOption(
        name="Weights & Biases",
        category="observability",
        description="ML experiment tracking with LLM support",
        pros=["Comprehensive ML platform", "Great visualizations", "Team collaboration"],
        cons=["Overkill for simple use cases", "Learning curve", "Can be expensive"],
        pricing_model="Free tier + $50/user/mo",
        estimated_monthly_base=50,
        estimated_per_request=0,
        best_for=["ML teams", "Experiment tracking", "Model comparison"],
        scale_fit=[ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://wandb.ai"
    ),
}

# Model Registry / Catalog Approaches
MODEL_REGISTRIES = {
    "mlflow": PlatformOption(
        name="MLflow",
        category="registry",
        description="Open-source ML lifecycle platform with model registry",
        pros=["Industry standard", "Provider agnostic", "Good versioning", "Databricks integration"],
        cons=["Self-hosting complexity", "UI could be better"],
        pricing_model="Open source / Databricks managed",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["ML teams", "Model versioning", "Experiment tracking"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH, ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.MEDIUM, ComplexityLevel.HIGH],
        url="https://mlflow.org"
    ),
    "huggingface_hub": PlatformOption(
        name="Hugging Face Hub",
        category="registry",
        description="Model hosting and versioning on Hugging Face",
        pros=["Large community", "Easy sharing", "Good for open models", "Spaces integration"],
        cons=["Limited private model features on free tier", "Not ideal for proprietary models"],
        pricing_model="Free tier + $9/mo Pro + Enterprise",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Open source models", "Community sharing", "Fine-tuned model hosting"],
        scale_fit=[ScaleCategory.STARTUP, ScaleCategory.GROWTH],
        complexity_fit=[ComplexityLevel.LOW, ComplexityLevel.MEDIUM],
        url="https://huggingface.co"
    ),
    "sagemaker_registry": PlatformOption(
        name="AWS SageMaker Model Registry",
        category="registry",
        description="AWS's managed model registry and deployment",
        pros=["AWS integration", "Enterprise features", "Good governance", "MLOps integration"],
        cons=["AWS lock-in", "Complex pricing", "Steep learning curve"],
        pricing_model="Usage-based (part of SageMaker)",
        estimated_monthly_base=50,
        estimated_per_request=0,
        best_for=["AWS-centric orgs", "Enterprise ML", "Regulated industries"],
        scale_fit=[ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.HIGH],
        url="https://aws.amazon.com/sagemaker/"
    ),
    "azure_ml_registry": PlatformOption(
        name="Azure ML Model Registry",
        category="registry",
        description="Azure's ML model management and deployment",
        pros=["Azure integration", "Good enterprise features", "OpenAI integration"],
        cons=["Azure lock-in", "Complex setup"],
        pricing_model="Usage-based (part of Azure ML)",
        estimated_monthly_base=50,
        estimated_per_request=0,
        best_for=["Azure-centric orgs", "Enterprise ML", "OpenAI/Azure OpenAI users"],
        scale_fit=[ScaleCategory.SCALE, ScaleCategory.ENTERPRISE],
        complexity_fit=[ComplexityLevel.HIGH],
        url="https://azure.microsoft.com/en-us/products/machine-learning"
    ),
    "simple_versioning": PlatformOption(
        name="Simple Version Control (Git + Config)",
        category="registry",
        description="Track model configs and prompts in Git",
        pros=["Simple", "Free", "Familiar workflow", "Full control"],
        cons=["Manual process", "No UI", "Limited governance"],
        pricing_model="Free",
        estimated_monthly_base=0,
        estimated_per_request=0,
        best_for=["Small teams", "Simple setups", "API-only usage"],
        scale_fit=[ScaleCategory.STARTUP],
        complexity_fit=[ComplexityLevel.LOW],
        url=""
    ),
}

# Use case templates for cost estimation
@dataclass
class UseCaseTemplate:
    name: str
    description: str
    typical_input_tokens: int
    typical_output_tokens: int
    requests_per_user_day: float
    model_tier: str  # "budget", "balanced", "premium" - for dynamic model matching
    complexity: ComplexityLevel

USE_CASE_TEMPLATES = {
    "chatbot_simple": UseCaseTemplate(
        name="Simple Chatbot",
        description="Basic Q&A chatbot with short responses",
        typical_input_tokens=500,
        typical_output_tokens=200,
        requests_per_user_day=10,
        model_tier="budget",
        complexity=ComplexityLevel.LOW
    ),
    "chatbot_advanced": UseCaseTemplate(
        name="Advanced Chatbot",
        description="Complex chatbot with context and longer responses",
        typical_input_tokens=2000,
        typical_output_tokens=800,
        requests_per_user_day=15,
        model_tier="balanced",
        complexity=ComplexityLevel.MEDIUM
    ),
    "rag_basic": UseCaseTemplate(
        name="Basic RAG",
        description="Document Q&A with retrieved context",
        typical_input_tokens=3000,
        typical_output_tokens=500,
        requests_per_user_day=20,
        model_tier="budget",
        complexity=ComplexityLevel.MEDIUM
    ),
    "rag_advanced": UseCaseTemplate(
        name="Advanced RAG",
        description="Complex RAG with large context and synthesis",
        typical_input_tokens=8000,
        typical_output_tokens=1500,
        requests_per_user_day=10,
        model_tier="balanced",
        complexity=ComplexityLevel.HIGH
    ),
    "code_generation": UseCaseTemplate(
        name="Code Generation",
        description="Code completion and generation tasks",
        typical_input_tokens=1500,
        typical_output_tokens=1000,
        requests_per_user_day=50,
        model_tier="balanced",
        complexity=ComplexityLevel.MEDIUM
    ),
    "code_review": UseCaseTemplate(
        name="Code Review Agent",
        description="Automated code review with detailed feedback",
        typical_input_tokens=5000,
        typical_output_tokens=2000,
        requests_per_user_day=5,
        model_tier="premium",
        complexity=ComplexityLevel.HIGH
    ),
    "summarization": UseCaseTemplate(
        name="Document Summarization",
        description="Summarizing long documents",
        typical_input_tokens=10000,
        typical_output_tokens=500,
        requests_per_user_day=5,
        model_tier="budget",
        complexity=ComplexityLevel.LOW
    ),
    "agent_workflow": UseCaseTemplate(
        name="Multi-Step Agent",
        description="Complex agent with multiple tool calls",
        typical_input_tokens=4000,
        typical_output_tokens=1500,
        requests_per_user_day=8,
        model_tier="balanced",
        complexity=ComplexityLevel.HIGH
    ),
    "data_extraction": UseCaseTemplate(
        name="Data Extraction",
        description="Structured data extraction from text",
        typical_input_tokens=2000,
        typical_output_tokens=300,
        requests_per_user_day=100,
        model_tier="budget",
        complexity=ComplexityLevel.LOW
    ),
    "content_generation": UseCaseTemplate(
        name="Content Generation",
        description="Marketing copy, articles, creative writing",
        typical_input_tokens=500,
        typical_output_tokens=2000,
        requests_per_user_day=10,
        model_tier="balanced",
        complexity=ComplexityLevel.MEDIUM
    ),
}

def get_all_platforms() -> Dict[str, Dict[str, PlatformOption]]:
    """Get all platform options organized by category."""
    return {
        "agent_frameworks": AGENT_FRAMEWORKS,
        "vector_stores": VECTOR_STORES,
        "cicd": CICD_APPROACHES,
        "observability": OBSERVABILITY_TOOLS,
        "registries": MODEL_REGISTRIES,
    }

def get_use_case_templates() -> Dict[str, UseCaseTemplate]:
    """Get all use case templates."""
    return USE_CASE_TEMPLATES

def _platforms(d):
    'Every PlatformOption as plain JSON, enums flattened to their values.'
    return {cat: {k: {**p.__dict__, 'scale_fit': [s.value for s in p.scale_fit],
                      'complexity_fit': [c.value for c in p.complexity_fit]}
                  for k, p in ps.items()} for cat, ps in d.items()}

def _use_cases(d): return {k: {**v.__dict__, 'complexity': v.complexity.value} for k, v in d.items()}

@cache
def page_data():
    'The whole catalogue as one JSON string, built once — nothing in it varies by request.'
    d = {'platforms': _platforms(get_all_platforms()), 'useCases': _use_cases(get_use_case_templates())}
    # `<` escaped because this lands inside a <script> tag: a `</script>` anywhere in a
    # description would otherwise end the tag early and spill the rest into the document.
    return json.dumps(d).replace('<', '\\u003c')
