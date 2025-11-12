import sys
import os

# Força o carregamento das variáveis de ambiente do .env
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

# Dados de teste
DADOS_TESTE = {
    "steam_appid": 999999,
    "detalhes": {"name": "Jogo Teste", "categoria": "Ação"},
    "reviews": {"total": 10, "positivos": 8}
}

# Comentando Supabase API por enquanto - JWT inválido
# print("Inserindo no Supabase...")
# SupabaseDB.inserir_dadosSteamRaw([DADOS_TESTE])
# print("Inserido no Supabase!")

print("Inserindo no Docker/Postgres via psycopg2...")
PostgreSQL.inserir_dadosSteamRaw_Bulk([DADOS_TESTE])
print("Inserido no Docker/Postgres!")

print("\nTeste de inserção concluído. Verificando no banco...")
