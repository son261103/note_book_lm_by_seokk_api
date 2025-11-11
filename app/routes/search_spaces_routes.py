from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import SearchSpace, get_async_session
from app.schemas import SearchSpaceCreate, SearchSpaceRead, SearchSpaceUpdate

router = APIRouter(tags=["search-spaces"])


@router.post("/searchspaces", response_model=SearchSpaceRead)
async def create_search_space(
    search_space: SearchSpaceCreate,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        db_search_space = SearchSpace(**search_space.model_dump())
        session.add(db_search_space)
        await session.commit()
        await session.refresh(db_search_space)
        return db_search_space
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create search space: {e!s}"
        ) from e


@router.get("/searchspaces", response_model=list[SearchSpaceRead])
async def read_search_spaces(
    skip: int = 0,
    limit: int = 200,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        result = await session.execute(
            select(SearchSpace).offset(skip).limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch search spaces: {e!s}"
        ) from e


@router.get("/searchspaces/{search_space_id}", response_model=SearchSpaceRead)
async def read_search_space(
    search_space_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    try:
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch search space: {e!s}"
        ) from e


@router.put("/searchspaces/{search_space_id}", response_model=SearchSpaceRead)
async def update_search_space(
    search_space_id: int,
    search_space_update: SearchSpaceUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        result = await session.execute(
            select(SearchSpace).filter(SearchSpace.id == search_space_id)
        )
        db_search_space = result.scalars().first()
        if not db_search_space:
            raise HTTPException(
                status_code=404,
                detail="Search space not found",
            )
        update_data = search_space_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_search_space, key, value)
        await session.commit()
        await session.refresh(db_search_space)
        return db_search_space
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update search space: {e!s}"
        ) from e


@router.delete("/searchspaces/{search_space_id}", response_model=dict)
async def delete_search_space(
    search_space_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        result = await session.execute(
            select(SearchSpace).filter(SearchSpace.id == search_space_id)
        )
        db_search_space = result.scalars().first()
        if not db_search_space:
            raise HTTPException(
                status_code=404,
                detail="Search space not found",
            )
        await session.delete(db_search_space)
        await session.commit()
        return {"message": "Search space deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete search space: {e!s}"
        ) from e
