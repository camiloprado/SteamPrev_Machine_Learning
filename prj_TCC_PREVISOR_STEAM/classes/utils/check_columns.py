"""Verifica estrutura das tabelas"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

db = PostgreSQL()
db.conectar()
cur = db._var_connConnection.cursor()

tabelas = ['steam_raw', 'steam_bd', 'steam_generico', 'steam_unificado', 'itad_raw', 'steam_itad_mapping']

for tabela in tabelas:
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{tabela}' ORDER BY ordinal_position")
    colunas = [r[0] for r in cur.fetchall()]
    print(f"\n{tabela}: {', '.join(colunas)}")

cur.close()
