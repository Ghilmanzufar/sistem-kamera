from sqlalchemy import text, inspect
from .connection import engine, Base

def auto_migrate_schema():
    """Otomatis membuat tabel dan menambahkan kolom baru ke PostgreSQL jika skema model diperbarui."""
    try:
        # 1. Buat tabel jika belum ada
        Base.metadata.create_all(bind=engine)

        # 2. Migrasi kolom baru pada tabel eksisting
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        with engine.connect() as conn:
            if "part_rules" in tables:
                cols = [c["name"] for c in inspector.get_columns("part_rules")]
                if "min_confidence" not in cols:
                    conn.execute(text("ALTER TABLE part_rules ADD COLUMN IF NOT EXISTS min_confidence DOUBLE PRECISION DEFAULT 0.70;"))
                if "avg_confidence" not in cols:
                    conn.execute(text("ALTER TABLE part_rules ADD COLUMN IF NOT EXISTS avg_confidence DOUBLE PRECISION DEFAULT 0.75;"))
                if "min_coverage" not in cols:
                    conn.execute(text("ALTER TABLE part_rules ADD COLUMN IF NOT EXISTS min_coverage DOUBLE PRECISION DEFAULT 1.0;"))
            
            if "inspection_logs" in tables:
                cols = [c["name"] for c in inspector.get_columns("inspection_logs")]
                if "operator_name" not in cols:
                    conn.execute(text("ALTER TABLE inspection_logs ADD COLUMN IF NOT EXISTS operator_name VARCHAR;"))
                if "method" not in cols:
                    conn.execute(text("ALTER TABLE inspection_logs ADD COLUMN IF NOT EXISTS method VARCHAR DEFAULT 'AI';"))
            
            conn.commit()
    except Exception as e:
        print(f"[WARN] Auto-migrate schema: {e}")
