from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.db import create_db_and_tables
from app.routes import router as crud_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Not needed if you setup a migration system like Alembic
    await create_db_and_tables()
    yield


# Swagger/OpenAPI Configuration
app = FastAPI(
    lifespan=lifespan,
    title="SurfSense API",
    description="""
## SurfSense Backend API Documentation

This is a comprehensive API for managing search spaces, documents, chats, podcasts, and various integrations.

### Features:
* 📚 **Search Spaces**: Manage your search spaces and configurations
* 📄 **Documents**: Upload and manage documents with various formats
* 💬 **Chats**: Interactive chat functionality with LLM integration
* 🎙️ **Podcasts**: Generate and manage podcasts from your content
* 🔌 **Connectors**: Integrate with Google Calendar, Gmail, Airtable, and Luma
* 🤖 **LLM Configs**: Configure and manage multiple LLM providers
* 📊 **Logs**: Track and monitor system activities

### Note:
All endpoints are public and do not require authentication.
    """,
    version="0.0.8",
    contact={
        "name": "SurfSense Team",
        "url": "https://github.com/yourusername/surfsense",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "search-spaces",
            "description": "Search space management - create, read, update, delete search spaces",
        },
        {
            "name": "documents",
            "description": "Document management - upload, process, and manage documents",
        },
        {
            "name": "chats",
            "description": "Chat operations - create conversations and interact with LLMs",
        },
        {
            "name": "podcasts",
            "description": "Podcast generation and management from documents or chats",
        },
        {
            "name": "llm-configs",
            "description": "LLM configuration management - configure multiple LLM providers",
        },
        {
            "name": "connectors",
            "description": "External service connectors - Google Calendar, Gmail, Airtable, Luma",
        },
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas section by default
        "docExpansion": "none",  # Collapse all tags by default
        "filter": True,  # Enable search filter
        "syntaxHighlight.theme": "monokai",  # Syntax highlighting theme
    },
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc UI
)

# Add ProxyHeaders middleware FIRST to trust proxy headers (e.g., from Cloudflare)
# This ensures FastAPI uses HTTPS in redirects when behind a proxy
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(crud_router, prefix="/api/v1")
