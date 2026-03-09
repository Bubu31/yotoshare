import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Run migrations for existing databases
    run_migrations()

    # Seed admin user from env vars if no users exist
    seed_admin_user()


def seed_admin_user():
    """Create the initial admin user from env vars if the users table is empty."""
    from app.models import User, Role

    db = SessionLocal()
    try:
        # Ensure admin user has role_id set
        admin_role = db.query(Role).filter(Role.name == "Admin").first()

        if db.query(User).count() == 0:
            username = settings.admin_username
            password_hash = settings.admin_password_hash
            if username and password_hash:
                admin = User(
                    username=username,
                    password_hash=password_hash,
                    role="admin",
                    role_id=admin_role.id if admin_role else None,
                )
                db.add(admin)
                db.commit()
                logger.info("Created admin user: %s", username)
            else:
                logger.warning("No admin credentials in env vars, skipping seed")
        else:
            logger.debug("Users table not empty, skipping seed")
    finally:
        db.close()


def run_migrations():
    """Add missing columns to existing tables and fix constraints"""
    from sqlalchemy import text

    # Add new columns
    column_migrations = [
        ("archives", "total_duration", "ALTER TABLE archives ADD COLUMN total_duration INTEGER"),
        ("archives", "chapters_count", "ALTER TABLE archives ADD COLUMN chapters_count INTEGER"),
        ("archives", "chapters_data", "ALTER TABLE archives ADD COLUMN chapters_data TEXT"),
        ("archives", "download_count", "ALTER TABLE archives ADD COLUMN download_count INTEGER DEFAULT 0"),
    ]

    with engine.connect() as conn:
        for table, column, sql in column_migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info("Added column %s to table %s", column, table)
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    logger.debug("Column %s already exists in table %s", column, table)
                else:
                    logger.error("Error adding column %s: %s", column, e)
                conn.rollback()

        # Fix author column to be nullable (SQLite requires table recreation)
        try:
            result = conn.execute(text("PRAGMA table_info(archives)"))
            columns_info = result.fetchall()
            author_col = next((col for col in columns_info if col[1] == "author"), None)

            if author_col and author_col[3] == 1:
                logger.info("Fixing author column to be nullable...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS archives_new (
                        id INTEGER PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        author VARCHAR(255),
                        description TEXT,
                        cover_path VARCHAR(500),
                        archive_path VARCHAR(500) NOT NULL,
                        file_size INTEGER DEFAULT 0,
                        total_duration INTEGER,
                        chapters_count INTEGER,
                        chapters_data TEXT,
                        discord_post_id VARCHAR(50),
                        download_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("""
                    INSERT INTO archives_new
                    SELECT id, title, author, description, cover_path, archive_path,
                           file_size, total_duration, chapters_count, chapters_data,
                           discord_post_id, download_count, created_at, updated_at
                    FROM archives
                """))
                conn.execute(text("DROP TABLE archives"))
                conn.execute(text("ALTER TABLE archives_new RENAME TO archives"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_archives_id ON archives (id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_archives_title ON archives (title)"))
                conn.commit()
                logger.info("Successfully made author column nullable")
            else:
                logger.debug("Author column is already nullable")
        except Exception as e:
            logger.error("Error fixing author column: %s", e)
            conn.rollback()

        # Add missing indexes
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_archives_discord_post_id ON archives (discord_post_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_download_tokens_expires_at ON download_tokens (expires_at)"))
            conn.commit()
        except Exception as e:
            logger.debug("Indexes already exist or error: %s", e)
            conn.rollback()

        # Create roles table and seed default roles
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    permissions TEXT NOT NULL,
                    is_system BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """))
            conn.commit()
            logger.info("Ensured roles table exists")
        except Exception as e:
            logger.error("Error creating roles table: %s", e)
            conn.rollback()

        # Seed default roles if they don't exist
        import json
        all_scopes = ["archives", "categories", "ages", "users", "roles", "discord", "packs"]

        # Admin: all permissions
        admin_perms = {scope: {"access": True, "modify": True, "delete": True} for scope in all_scopes}
        # Editor: access+modify on most, no users/roles management
        editor_perms = {}
        for scope in all_scopes:
            if scope in ("users", "roles"):
                editor_perms[scope] = {"access": False, "modify": False, "delete": False}
            else:
                editor_perms[scope] = {"access": True, "modify": True, "delete": False}

        try:
            result = conn.execute(text("SELECT COUNT(*) FROM roles WHERE name = 'Admin'"))
            if result.scalar() == 0:
                conn.execute(
                    text("INSERT INTO roles (name, description, permissions, is_system) VALUES (:name, :desc, :perms, 1)"),
                    {"name": "Admin", "desc": "Accès complet à toutes les fonctionnalités", "perms": json.dumps(admin_perms)}
                )
                logger.info("Seeded Admin role")

            result = conn.execute(text("SELECT COUNT(*) FROM roles WHERE name = 'Éditeur'"))
            if result.scalar() == 0:
                conn.execute(
                    text("INSERT INTO roles (name, description, permissions, is_system) VALUES (:name, :desc, :perms, 1)"),
                    {"name": "Éditeur", "desc": "Accès en lecture et modification, pas de suppression", "perms": json.dumps(editor_perms)}
                )
                logger.info("Seeded Éditeur role")
            conn.commit()
        except Exception as e:
            logger.error("Error seeding default roles: %s", e)
            conn.rollback()

        # Add role_id column to users if missing
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id)"))
            conn.commit()
            logger.info("Added role_id column to users table")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.debug("Column role_id already exists in users table")
            else:
                logger.error("Error adding role_id column: %s", e)
            conn.rollback()

        # Add reusable column to download_tokens
        try:
            conn.execute(text("ALTER TABLE download_tokens ADD COLUMN reusable BOOLEAN DEFAULT 0"))
            conn.commit()
            logger.info("Added reusable column to download_tokens table")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.debug("Column reusable already exists in download_tokens table")
            else:
                logger.error("Error adding reusable column: %s", e)
            conn.rollback()

        # Create packs table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS packs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    image_path VARCHAR(500),
                    expires_at DATETIME NOT NULL,
                    created_by INTEGER REFERENCES users(id),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_packs_token ON packs (token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_packs_expires_at ON packs (expires_at)"))
            conn.commit()
            logger.info("Ensured packs table exists")
        except Exception as e:
            logger.error("Error creating packs table: %s", e)
            conn.rollback()

        # Create pack_archives association table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pack_archives (
                    pack_id INTEGER NOT NULL REFERENCES packs(id) ON DELETE CASCADE,
                    archive_id INTEGER NOT NULL REFERENCES archives(id) ON DELETE CASCADE,
                    position INTEGER DEFAULT 0,
                    PRIMARY KEY (pack_id, archive_id)
                )
            """))
            conn.commit()
            logger.info("Ensured pack_archives table exists")
        except Exception as e:
            logger.error("Error creating pack_archives table: %s", e)
            conn.rollback()

        # Create pack_assets table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pack_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_type VARCHAR(50) UNIQUE NOT NULL,
                    filename VARCHAR(500) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Ensured pack_assets table exists")
        except Exception as e:
            logger.error("Error creating pack_assets table: %s", e)
            conn.rollback()

        # Add packs scope to existing roles that don't have it
        try:
            rows = conn.execute(text("SELECT id, name, permissions FROM roles")).fetchall()
            for role_id, role_name, perms_json in rows:
                try:
                    perms = json.loads(perms_json) if perms_json else {}
                except (json.JSONDecodeError, TypeError):
                    perms = {}
                if "packs" not in perms:
                    if role_name == "Admin":
                        perms["packs"] = {"access": True, "modify": True, "delete": True}
                    else:
                        perms["packs"] = {"access": True, "modify": True, "delete": False}
                    conn.execute(
                        text("UPDATE roles SET permissions = :perms WHERE id = :rid"),
                        {"perms": json.dumps(perms), "rid": role_id}
                    )
            conn.commit()
            logger.info("Ensured packs scope exists in all roles")
        except Exception as e:
            logger.error("Error adding packs scope to roles: %s", e)
            conn.rollback()

        # Add discord_post_id to packs table
        try:
            conn.execute(text("ALTER TABLE packs ADD COLUMN discord_post_id VARCHAR(50)"))
            conn.commit()
            logger.info("Added discord_post_id column to packs table")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.debug("Column discord_post_id already exists in packs table")
            else:
                logger.error("Error adding discord_post_id column to packs: %s", e)
            conn.rollback()

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_packs_discord_post_id ON packs (discord_post_id)"))
            conn.commit()
        except Exception as e:
            logger.debug("Index ix_packs_discord_post_id already exists or error: %s", e)
            conn.rollback()

        # Migrate existing users: map role string to role_id
        try:
            result = conn.execute(text("SELECT id FROM roles WHERE name = 'Admin'"))
            admin_role_row = result.fetchone()
            result = conn.execute(text("SELECT id FROM roles WHERE name = 'Éditeur'"))
            editor_role_row = result.fetchone()

            if admin_role_row and editor_role_row:
                admin_role_id = admin_role_row[0]
                editor_role_id = editor_role_row[0]

                conn.execute(
                    text("UPDATE users SET role_id = :rid WHERE role = 'admin' AND role_id IS NULL"),
                    {"rid": admin_role_id}
                )
                conn.execute(
                    text("UPDATE users SET role_id = :rid WHERE role = 'editor' AND role_id IS NULL"),
                    {"rid": editor_role_id}
                )
                conn.commit()
                logger.info("Migrated existing users to role_id")
        except Exception as e:
            logger.error("Error migrating users to role_id: %s", e)
            conn.rollback()
