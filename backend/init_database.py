#!/usr/bin/env python3
"""
Database Initialization Script for Agent-Chat
Creates all tables and initial data
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.database import Base
from core.config import settings
import models  # Import all models to register them

# Colors for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


async def init_database():
    """Initialize database schema"""
    print(f"{BLUE}====================================={NC}")
    print(f"{BLUE}Agent-Chat Database Initialization{NC}")
    print(f"{BLUE}====================================={NC}")
    print()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL", settings.database_url)
    
    # Hide password in output
    display_url = db_url.split('@')[1] if '@' in db_url else db_url
    print(f"{YELLOW}Database:{NC} ...@{display_url}")
    print()
    
    try:
        # Create engine
        engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        # Test connection
        print(f"{YELLOW}Testing connection...{NC}")
        async with engine.connect() as conn:
            result = await conn.execute("SELECT version()")
            version = result.scalar()
            print(f"{GREEN}✓ Connected successfully{NC}")
            print(f"  Database: PostgreSQL")
            print(f"  Version: {version.split(',')[0] if version else 'Unknown'}")
            print()
        
        # Create all tables
        print(f"{YELLOW}Creating database schema...{NC}")
        async with engine.begin() as conn:
            # Drop all tables (BE CAREFUL - only for initial setup)
            # await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print(f"{GREEN}✓ Schema created successfully{NC}")
        print()
        
        # Verify tables
        print(f"{YELLOW}Verifying tables...{NC}")
        async with engine.connect() as conn:
            # Get list of tables
            result = await conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = result.fetchall()
            
            print(f"  Created {len(tables)} tables:")
            for table in tables:
                print(f"    • {table[0]}")
        
        print()
        
        # Create initial data (optional)
        print(f"{YELLOW}Creating initial data...{NC}")
        
        # Create async session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Check if we need to create default user
            from models import User
            from sqlalchemy import select
            
            result = await session.execute(select(User).limit(1))
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                # Create a default admin user (optional)
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                
                admin_user = User(
                    email="admin@bpchat.local",
                    username="admin",
                    hashed_password=pwd_context.hash("changeme"),
                    full_name="Admin User",
                    is_active=True,
                    roles=["admin", "user"]
                )
                
                session.add(admin_user)
                await session.commit()
                
                print(f"{GREEN}✓ Created default admin user{NC}")
                print(f"    Username: admin")
                print(f"    Password: changeme")
                print(f"    {YELLOW}⚠ Change this password immediately!{NC}")
            else:
                print(f"  Users already exist, skipping default user creation")
        
        await engine.dispose()
        
        print()
        print(f"{BLUE}====================================={NC}")
        print(f"{GREEN}Database initialization complete!{NC}")
        print(f"{BLUE}====================================={NC}")
        print()
        print(f"{YELLOW}Next steps:{NC}")
        print("1. Update the admin password if created")
        print("2. Start the application")
        print("3. Test the API endpoints")
        
        return True
        
    except Exception as e:
        print()
        print(f"{RED}✗ Database initialization failed{NC}")
        print(f"  Error: {str(e)}")
        print()
        print(f"{YELLOW}Troubleshooting:{NC}")
        print("1. Check your DATABASE_URL in .env.production")
        print("2. Ensure the database exists (run setup-agion-database.sh)")
        print("3. Verify network connectivity to the database")
        print("4. Check if the user has proper permissions")
        return False


async def verify_connection():
    """Quick connection verification"""
    db_url = os.getenv("DATABASE_URL", settings.database_url)
    
    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            await engine.dispose()
            return True
    except Exception as e:
        print(f"{RED}Connection failed: {e}{NC}")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent-Chat Database Initialization")
    parser.add_argument(
        "--verify", 
        action="store_true", 
        help="Only verify connection without creating tables"
    )
    parser.add_argument(
        "--drop-all",
        action="store_true",
        help="Drop all tables before creating (DANGEROUS!)"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        print(f"{YELLOW}Verifying database connection...{NC}")
        result = asyncio.run(verify_connection())
        if result:
            print(f"{GREEN}✓ Connection successful{NC}")
            sys.exit(0)
        else:
            print(f"{RED}✗ Connection failed{NC}")
            sys.exit(1)
    
    # Run initialization
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
