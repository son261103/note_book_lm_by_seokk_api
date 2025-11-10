from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import config
from app.db import User, create_db_and_tables, get_async_session
from app.routes import router as crud_router
from app.schemas import UserCreate, UserRead, UserUpdate
from app.users import SECRET, auth_backend, current_active_user, fastapi_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Not needed if you setup a migration system like Alembic
    await create_db_and_tables()
    yield


def registration_allowed():
    if not config.REGISTRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Registration is disabled"
        )
    return True


# Swagger/OpenAPI Configuration
app = FastAPI(
    lifespan=lifespan,
    title="SurfSense API",
    description="""
## SurfSense Backend API Documentation

This is a comprehensive API for managing search spaces, documents, chats, podcasts, and various integrations.

### Features:
* 🔐 **Authentication**: JWT-based authentication with Google OAuth support
* 📚 **Search Spaces**: Manage your search spaces and configurations
* 📄 **Documents**: Upload and manage documents with various formats
* 💬 **Chats**: Interactive chat functionality with LLM integration
* 🎙️ **Podcasts**: Generate and manage podcasts from your content
* 🔌 **Connectors**: Integrate with Google Calendar, Gmail, Airtable, and Luma
* 🤖 **LLM Configs**: Configure and manage multiple LLM providers
* 📊 **Logs**: Track and monitor system activities

### Authentication:
Most endpoints require authentication. Use the `/auth/jwt/login` endpoint to obtain a JWT token,
then include it in the `Authorization` header as `Bearer <token>`.
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
            "name": "auth",
            "description": "Authentication operations including login, register, password reset, and OAuth",
        },
        {
            "name": "users",
            "description": "User management operations",
        },
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
        {
            "name": "logs",
            "description": "System logs and activity tracking",
        },
        {
            "name": "crud",
            "description": "General CRUD operations",
        },
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas section by default
        "docExpansion": "list",  # Expand only tags by default
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

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(registration_allowed)],  # blocks registration when disabled
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

if config.AUTH_TYPE == "GOOGLE":
    from app.users import google_oauth_client

    app.include_router(
        fastapi_users.get_oauth_router(
            google_oauth_client, auth_backend, SECRET, is_verified_by_default=True
        )
        if not config.BACKEND_URL
        else fastapi_users.get_oauth_router(
            google_oauth_client,
            auth_backend,
            SECRET,
            is_verified_by_default=True,
            redirect_url=f"{config.BACKEND_URL}/auth/google/callback",
        ),
        prefix="/auth/google",
        tags=["auth"],
        dependencies=[
            Depends(registration_allowed)
        ],  # blocks OAuth registration when disabled
    )

app.include_router(crud_router, prefix="/api/v1", tags=["crud"])


@app.get("/verify-token")
async def authenticated_route(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return {"message": "Token is valid"}
