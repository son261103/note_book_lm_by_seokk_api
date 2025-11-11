from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db import (
    LLMConfig,
    SearchSpace,
    get_async_session,
)
from app.schemas import LLMConfigCreate, LLMConfigRead, LLMConfigUpdate
from app.services.llm_service import validate_llm_config

router = APIRouter(tags=["llm-configs"])


# Helper function to verify search space exists
async def verify_search_space_exists(
    session: AsyncSession, search_space_id: int
) -> SearchSpace:
    """Verify that the search space exists"""
    result = await session.execute(
        select(SearchSpace).filter(SearchSpace.id == search_space_id)
    )
    search_space = result.scalars().first()
    if not search_space:
        raise HTTPException(
            status_code=404,
            detail="Search space not found",
        )
    return search_space


@router.post("/llm-configs", response_model=LLMConfigRead)
async def create_llm_config(
    llm_config: LLMConfigCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new LLM configuration for a search space"""
    try:
        # Verify search space exists
        await verify_search_space_exists(session, llm_config.search_space_id)

        # Validate the LLM configuration by making a test API call
        is_valid, error_message = await validate_llm_config(
            provider=llm_config.provider.value,
            model_name=llm_config.model_name,
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
            custom_provider=llm_config.custom_provider,
            litellm_params=llm_config.litellm_params,
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid LLM configuration: {error_message}",
            )

        db_llm_config = LLMConfig(**llm_config.model_dump())
        session.add(db_llm_config)
        await session.commit()
        await session.refresh(db_llm_config)
        return db_llm_config
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create LLM configuration: {e!s}"
        ) from e


@router.get("/llm-configs", response_model=list[LLMConfigRead])
async def read_llm_configs(
    search_space_id: int,
    skip: int = 0,
    limit: int = 200,
    session: AsyncSession = Depends(get_async_session),
):
    """Get all LLM configurations for a search space"""
    try:
        # Verify search space exists
        await verify_search_space_exists(session, search_space_id)

        result = await session.execute(
            select(LLMConfig)
            .filter(LLMConfig.search_space_id == search_space_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch LLM configurations: {e!s}"
        ) from e


@router.get("/llm-configs/{llm_config_id}", response_model=LLMConfigRead)
async def read_llm_config(
    llm_config_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific LLM configuration by ID"""
    try:
        # Get the LLM config
        result = await session.execute(
            select(LLMConfig).filter(LLMConfig.id == llm_config_id)
        )
        llm_config = result.scalars().first()

        if not llm_config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")

        return llm_config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch LLM configuration: {e!s}"
        ) from e


@router.put("/llm-configs/{llm_config_id}", response_model=LLMConfigRead)
async def update_llm_config(
    llm_config_id: int,
    llm_config_update: LLMConfigUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update an existing LLM configuration"""
    try:
        # Get the LLM config
        result = await session.execute(
            select(LLMConfig).filter(LLMConfig.id == llm_config_id)
        )
        db_llm_config = result.scalars().first()

        if not db_llm_config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")

        update_data = llm_config_update.model_dump(exclude_unset=True)

        # Apply updates to a temporary copy for validation
        temp_config = {
            "provider": update_data.get("provider", db_llm_config.provider.value),
            "model_name": update_data.get("model_name", db_llm_config.model_name),
            "api_key": update_data.get("api_key", db_llm_config.api_key),
            "api_base": update_data.get("api_base", db_llm_config.api_base),
            "custom_provider": update_data.get(
                "custom_provider", db_llm_config.custom_provider
            ),
            "litellm_params": update_data.get(
                "litellm_params", db_llm_config.litellm_params
            ),
        }

        # Validate the updated configuration
        is_valid, error_message = await validate_llm_config(
            provider=temp_config["provider"],
            model_name=temp_config["model_name"],
            api_key=temp_config["api_key"],
            api_base=temp_config["api_base"],
            custom_provider=temp_config["custom_provider"],
            litellm_params=temp_config["litellm_params"],
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid LLM configuration: {error_message}",
            )

        # Apply updates to the database object
        for key, value in update_data.items():
            setattr(db_llm_config, key, value)

        await session.commit()
        await session.refresh(db_llm_config)
        return db_llm_config
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update LLM configuration: {e!s}"
        ) from e


@router.delete("/llm-configs/{llm_config_id}", response_model=dict)
async def delete_llm_config(
    llm_config_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete an LLM configuration"""
    try:
        # Get the LLM config
        result = await session.execute(
            select(LLMConfig).filter(LLMConfig.id == llm_config_id)
        )
        db_llm_config = result.scalars().first()

        if not db_llm_config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")

        await session.delete(db_llm_config)
        await session.commit()
        return {"message": "LLM configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete LLM configuration: {e!s}"
        ) from e
