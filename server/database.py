"""
Database configuration and connection utilities for Social Media Agent
"""
import os
import asyncio
from typing import Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from databases import Database
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/social_media_agent"
)

# For async operations
database = Database(DATABASE_URL)

# For sync operations with SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increase pool size
    max_overflow=30,  # Increase overflow
    pool_timeout=30,  # Increase timeout
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True  # Test connections before use
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy base
Base = declarative_base()

# Metadata for database operations
metadata = MetaData()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for handling connections and operations"""
    
    def __init__(self):
        self.database = database
        self.engine = engine
    
    async def connect(self):
        """Connect to the database"""
        try:
            await self.database.connect()
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the database"""
        try:
            await self.database.disconnect()
            logger.info("Database disconnected successfully")
        except Exception as e:
            logger.error(f"Failed to disconnect from database: {e}")
            raise
    
    def get_sync_session(self):
        """Get a synchronous database session"""
        return SessionLocal()
    
    async def execute_query(self, query: str, values: dict = None):
        """Execute a raw SQL query"""
        try:
            return await self.database.execute(query=query, values=values or {})
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
    
    async def fetch_one(self, query: str, values: dict = None):
        """Fetch one record from database"""
        try:
            return await self.database.fetch_one(query=query, values=values or {})
        except Exception as e:
            logger.error(f"Failed to fetch one record: {e}")
            raise
    
    async def fetch_all(self, query: str, values: dict = None):
        """Fetch all records from database"""
        try:
            return await self.database.fetch_all(query=query, values=values or {})
        except Exception as e:
            logger.error(f"Failed to fetch all records: {e}")
            raise


# Global database manager instance
db_manager = DatabaseManager()


def get_database():
    """Dependency to get database instance"""
    return db_manager.database


def get_sync_db():
    """Dependency to get sync database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        await database.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def parse_sql_statements(sql_content: str) -> list:
    """Parse SQL content into individual statements, handling dollar-quoted functions"""
    statements = []
    current_statement = ""
    in_dollar_quote = False
    dollar_tag = None
    
    lines = sql_content.split('\n')
    
    for line in lines:
        stripped_line = line.strip()
        
        # Skip empty lines and comments when not in dollar quote
        if not in_dollar_quote and (not stripped_line or stripped_line.startswith('--')):
            continue
            
        current_statement += line + '\n'
        
        # Check for dollar-quoted strings (PostgreSQL function definitions)
        if '$$' in line:
            dollar_positions = []
            pos = 0
            while True:
                pos = line.find('$$', pos)
                if pos == -1:
                    break
                dollar_positions.append(pos)
                pos += 2
            
            for dollar_pos in dollar_positions:
                if not in_dollar_quote:
                    # Starting a dollar quote - find the tag
                    start_pos = dollar_pos
                    while start_pos > 0 and line[start_pos - 1].isalnum():
                        start_pos -= 1
                    tag_start = start_pos
                    
                    end_pos = dollar_pos + 2
                    while end_pos < len(line) and line[end_pos].isalnum():
                        end_pos += 1
                    
                    dollar_tag = line[tag_start:end_pos]
                    in_dollar_quote = True
                else:
                    # Check if this ends the current dollar quote
                    tag_start = dollar_pos
                    while tag_start > 0 and line[tag_start - 1].isalnum():
                        tag_start -= 1
                    
                    tag_end = dollar_pos + 2
                    while tag_end < len(line) and line[tag_end].isalnum():
                        tag_end += 1
                    
                    current_tag = line[tag_start:tag_end]
                    if current_tag == dollar_tag:
                        in_dollar_quote = False
                        dollar_tag = None
        
        # Check for statement end (semicolon) when not in dollar quote
        if not in_dollar_quote and line.rstrip().endswith(';'):
            statement = current_statement.strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
            current_statement = ""
    
    # Add any remaining statement
    if current_statement.strip():
        statement = current_statement.strip()
        if statement and not statement.startswith('--'):
            statements.append(statement)
    
    return statements

async def check_and_run_migrations():
    """Check if migrations need to be run and execute them"""
    try:
        # Check if posts table exists and what columns it has
        result = await database.fetch_one(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'posts' AND column_name IN ('platform', 'platforms')"
        )
        
        if result and result['column_name'] == 'platform':
            # Need to migrate from platform to platforms
            logger.info("Migrating from 'platform' column to 'platforms' array...")
            migration_path = os.path.join(os.path.dirname(__file__), "migrate_platforms_column.sql")
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                statements = parse_sql_statements(migration_sql)
                
                for statement in statements:
                    try:
                        await database.execute(statement)
                    except Exception as e:
                        logger.warning(f"Migration statement warning: {e}")
                
                logger.info("Platform to platforms migration completed")
            else:
                logger.warning("Migration file not found, but migration needed")
        
        # Check if social_media_accounts table exists
        try:
            table_exists_result = await database.fetch_one(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'social_media_accounts') AS exists"
            )
            table_exists = table_exists_result and table_exists_result.get('exists', False) if table_exists_result else False
        except Exception as e:
            logger.debug(f"Error checking for social_media_accounts table: {e}")
            table_exists = False
        
        if not table_exists:
            # Need to create social_media_accounts table
            logger.info("Creating social_media_accounts table...")
            migration_path = os.path.join(os.path.dirname(__file__), "migrate_social_media_accounts.sql")
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                statements = parse_sql_statements(migration_sql)
                
                for statement in statements:
                    try:
                        await database.execute(statement)
                        logger.debug(f"Executed migration statement: {statement[:100]}...")
                    except Exception as e:
                        error_msg = str(e).lower()
                        if any(keyword in error_msg for keyword in [
                            "already exists", "duplicate key", "relation already exists",
                            "constraint already exists", "index already exists",
                            "function already exists", "trigger already exists"
                        ]):
                            logger.debug(f"Migration object already exists: {e}")
                        else:
                            logger.warning(f"Migration statement warning: {e}")
                
                logger.info("Social media accounts table migration completed")
            else:
                logger.warning("Social media accounts migration file not found")
        
        # Check if password_hash column exists in users table
        try:
            column_exists_result = await database.fetch_one(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'password_hash') AS exists"
            )
            column_exists = column_exists_result and column_exists_result.get('exists', False) if column_exists_result else False
        except Exception as e:
            logger.debug(f"Error checking for password_hash column: {e}")
            column_exists = False
        
        if not column_exists:
            # Need to add password_hash column
            logger.info("Adding password_hash column to users table...")
            migration_path = os.path.join(os.path.dirname(__file__), "migrate_add_password.sql")
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                statements = parse_sql_statements(migration_sql)
                
                for statement in statements:
                    try:
                        await database.execute(statement)
                        logger.debug(f"Executed migration statement: {statement[:100]}...")
                    except Exception as e:
                        error_msg = str(e).lower()
                        if any(keyword in error_msg for keyword in [
                            "already exists", "duplicate key", "relation already exists",
                            "constraint already exists", "index already exists",
                            "column already exists"
                        ]):
                            logger.debug(f"Migration object already exists: {e}")
                        else:
                            logger.warning(f"Migration statement warning: {e}")
                
                logger.info("Password hash column migration completed")
            else:
                logger.warning("Password migration file not found")
        
        return True
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        return False

async def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        # Check if we can connect
        if not await check_database_connection():
            logger.error("Cannot connect to database for initialization")
            return False
        
        # Read and execute schema file
        schema_path = os.path.join(os.path.dirname(__file__), "database_schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                
            # Parse SQL statements properly, handling dollar-quoted functions
            statements = parse_sql_statements(schema_sql)
            
            successful_statements = 0
            failed_statements = 0
            
            for i, statement in enumerate(statements):
                try:
                    logger.debug(f"Executing statement {i+1}/{len(statements)}")
                    await database.execute(statement)
                    successful_statements += 1
                except Exception as e:
                    # Categorize errors for better handling
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in [
                        "already exists", "duplicate key", "relation already exists",
                        "constraint already exists", "index already exists",
                        "function already exists", "trigger already exists"
                    ]):
                        logger.debug(f"Schema object already exists (statement {i+1}): {e}")
                        successful_statements += 1
                    else:
                        failed_statements += 1
                        logger.warning(f"Schema statement failed (statement {i+1}): {e}")
                        logger.debug(f"Failed statement: {statement[:500]}...")
                        
                        # For critical errors, stop initialization
                        if any(critical in error_msg for critical in [
                            "syntax error", "column does not exist", "relation does not exist"
                        ]):
                            logger.error(f"Critical database error, stopping initialization: {e}")
                            return False
            
            logger.info(f"Database schema initialization completed: "
                       f"{successful_statements} successful, {failed_statements} failed statements")
            
            # Run any necessary migrations
            await check_and_run_migrations()
            
            return True
        else:
            logger.error("Database schema file not found")
            return False
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False


async def create_tables():
    """Create all tables using SQLAlchemy metadata"""
    try:
        # Import models to register them with Base
        from . import models  # This will be created next
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def get_database_info():
    """Get database connection information"""
    return {
        "database_url": DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else "Not configured",
        "engine": str(engine.url).split('@')[1] if '@' in str(engine.url) else "Not configured",
        "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else "Unknown"
    }


# Startup and shutdown events for FastAPI
async def startup_db():
    """Database startup handler"""
    try:
        await db_manager.connect()
        await initialize_database()
        logger.info("Database startup completed")
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise


async def shutdown_db():
    """Database shutdown handler"""
    try:
        await db_manager.disconnect()
        logger.info("Database shutdown completed")
    except Exception as e:
        logger.error(f"Database shutdown failed: {e}")
