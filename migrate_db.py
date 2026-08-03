from sqlalchemy import text
from database_config import engine

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE part_rules ADD COLUMN IF NOT EXISTS min_confidence FLOAT DEFAULT 0.70"))
    conn.execute(text("ALTER TABLE part_rules ADD COLUMN IF NOT EXISTS avg_confidence FLOAT DEFAULT 0.75"))
    conn.execute(text("ALTER TABLE part_rules ADD COLUMN IF NOT EXISTS min_coverage FLOAT DEFAULT 1.0"))
    conn.commit()
    print("Migration berhasil: kolom min_confidence, avg_confidence, dan min_coverage ditambahkan.")
