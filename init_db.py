#!/usr/bin/env python
"""Initialize Vercel Postgres database with tables."""
import sys
import os
from dotenv import load_dotenv

# Load from .env.local first, then .env
load_dotenv('.env.local')
load_dotenv()

# Debug: show what DATABASE_URL is set to
db_url = os.getenv('DATABASE_URL', 'NOT FOUND')
print(f"[DEBUG] DATABASE_URL: {db_url[:60]}..." if len(db_url) > 60 else f"[DEBUG] DATABASE_URL: {db_url}")

from app import app, db

try:
    with app.app_context():
        db.create_all()
        print('\n✅ Tabelas criadas/verificadas com sucesso no Postgres remoto')
except Exception as e:
    print(f'\n❌ Erro ao criar tabelas: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
