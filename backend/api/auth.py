"""
Authentication API endpoints for Agent-Chat
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional

from core.database import get_db
from core.auth import (
    Token, UserAuth, 
    verify_password, get_password_hash,
    create_access_token, create_refresh_token,
    get_current_active_user, TokenData
)
from models import User
from api.validators import SanitizedStr
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()


class UserCreate(BaseModel):
    """User registration model"""
    username: SanitizedStr = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class UserResponse(BaseModel):
    """User response model"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    roles: list


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if user exists
    result = await db.execute(
        select(User).where(
            (User.username == user_data.username) |
            (User.email == user_data.email)
        )
    )
    existing_user = result.scalars().first()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        roles=["user"]  # Default role
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        roles=new_user.roles
    )


@router.post("/login", response_model=Token)
async def login(
    user_auth: UserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Login and receive access token"""
    # Get user from database
    result = await db.execute(
        select(User).where(User.username == user_auth.username)
    )
    user = result.scalars().first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(user_auth.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create tokens
    access_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "roles": user.roles
    }
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(access_token_data)
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    from core.auth import verify_token
    
    # Verify refresh token
    try:
        token_data = verify_token(refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.username == token_data.username)
    )
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "roles": user.roles
    }
    
    new_access_token = create_access_token(access_token_data)
    
    return Token(
        access_token=new_access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information"""
    result = await db.execute(
        select(User).where(User.username == current_user.username)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=user.roles
    )


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_active_user)):
    """Logout user (client should remove token)"""
    # In a more complex implementation, you might want to:
    # - Add token to a blacklist
    # - Invalidate refresh tokens
    # - Log the logout event
    
    return {"message": "Successfully logged out"}
