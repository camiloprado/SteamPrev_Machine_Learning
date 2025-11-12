"""
Teste da Arquitetura Híbrida de Dados
======================================

ARQUITETURA:
-----------
1. DOCKER/PostgreSQL LOCAL (localhost:5432)
   - Tabelas: steam_raw, itad_raw
   - Propósito: Armazenar dados BRUTOS em grande volume (JSONB)
   - Método: PostgreSQL.inserir_dadosSteamRaw() via psycopg2
   
2. SUPABASE CLOUD (API REST)
   - Tabelas: steam_bd, steam_generico
   - Propósito: Dados LIMPOS e ESTRUTURADOS para consulta/visualização
   - Método: SupabaseDB.inserir_dadosSteamBD() via API REST

FLUXO:
------
Steam API → steam_raw (Docker) → Processamento → steam_bd (Supabase Cloud)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

# ========================================
# DADOS DE TESTE
# ========================================

# 1. Dados BRUTOS da Steam API (como vem da API)
DADOS_RAW = {
    "steam_appid": 888888,
    "detalhes": {
        "type": "game",
        "name": "Test Game - Hybrid Architecture",
        "steam_appid": 888888,
        "required_age": 0,
        "is_free": False,
        "detailed_description": "Este é um jogo de teste para validar a arquitetura híbrida...",
        "short_description": "Jogo de teste",
        "supported_languages": "English, Portuguese-Brazil",
        "developers": ["Test Studio"],
        "publishers": ["Test Publisher"],
        "price_overview": {
            "currency": "BRL",
            "initial": 4999,
            "final": 4999,
            "discount_percent": 0
        },
        "metacritic": {
            "score": 85
        },
        "categories": [
            {"id": 2, "description": "Single-player"},
            {"id": 22, "description": "Steam Achievements"}
        ],
        "genres": [
            {"id": "1", "description": "Action"},
            {"id": "25", "description": "Adventure"}
        ],
        "release_date": {
            "coming_soon": False,
            "date": "12 Nov, 2025"
        }
    },
    "reviews": {
        "query_summary": {
            "total_reviews": 1500,
            "total_positive": 1200,
            "total_negative": 300,
            "review_score": 80,
            "review_score_desc": "Very Positive"
        }
    }
}

# 2. Dados ESTRUTURADOS (processados para o Supabase)
DADOS_ESTRUTURADOS = {
    "appid": 888888,
    "nome": "Test Game - Hybrid Architecture",
    "classificacao_etaria": "0",
    "linguagens": ["English", "Portuguese-Brazil"],
    "desenvolvedores": ["Test Studio"],
    "distribuidores": ["Test Publisher"],
    "preco": "R$ 49.99",
    "metacritic_score": "85",
    "categorias": ["Single-player", "Steam Achievements"],
    "genero": ["Action", "Adventure"],
    "data_lancamento": "12 Nov, 2025",
    "review_score": 80,
    "total_reviews": 1500,
    "total_negative": 300,
    "total_positive": 1200,
    "review_score_desc": "Very Positive"
}

# ========================================
# EXECUÇÃO DO TESTE
# ========================================

print("=" * 70)
print("TESTE DA ARQUITETURA HÍBRIDA DE DADOS")
print("=" * 70)

# PASSO 1: Inserir dados BRUTOS no Docker/PostgreSQL
print("\n[PASSO 1] Inserindo dados BRUTOS no Docker/PostgreSQL (steam_raw)...")
print(f"  → AppID: {DADOS_RAW['steam_appid']}")
print(f"  → Tabela: steam_raw")
print(f"  → Método: PostgreSQL.inserir_dadosSteamRaw_Bulk()")

try:
    PostgreSQL.inserir_dadosSteamRaw_Bulk([DADOS_RAW])
    print("  ✓ Dados brutos inseridos com sucesso no Docker!")
except Exception as e:
    print(f"  ✗ Erro: {e}")

# PASSO 2: Inserir dados ESTRUTURADOS no Supabase Cloud
print("\n[PASSO 2] Inserindo dados ESTRUTURADOS no Supabase Cloud (steam_bd)...")
print(f"  → AppID: {DADOS_ESTRUTURADOS['appid']}")
print(f"  → Tabela: steam_bd")
print(f"  → Método: SupabaseDB.inserir_dadosSteamBD()")

try:
    SupabaseDB.inserir_dadosSteamBD([DADOS_ESTRUTURADOS])
    print("  ✓ Dados estruturados inseridos com sucesso no Supabase!")
except Exception as e:
    print(f"  ✗ Erro: {e}")

# PASSO 3: Verificação
print("\n" + "=" * 70)
print("VERIFICAÇÃO DOS DADOS")
print("=" * 70)

print("\n[DOCKER] Verificando steam_raw:")
print("  Execute: docker exec -it supabase-db psql -U postgres -d postgres \\")
print("           -c \"SELECT appid, detalhes->>'name' as nome FROM steam_raw WHERE appid = 888888;\"")

print("\n[SUPABASE] Verificando steam_bd:")
print("  1. Acesse: https://supabase.com/dashboard")
print("  2. Projeto: norphjcxnsgklyutnmin")
print("  3. Table Editor → steam_bd")
print("  4. Filtro: appid = 888888")

print("\n" + "=" * 70)
print("RESUMO DA ARQUITETURA")
print("=" * 70)
print("""
┌─────────────────────────────────────────────────────────────────┐
│                      FLUXO DE DADOS                             │
└─────────────────────────────────────────────────────────────────┘

  Steam API (280k+ jogos)
       │
       ├─────────────────────────────────────────────┐
       │                                             │
       ▼                                             ▼
  [DADOS BRUTOS]                              [PROCESSAMENTO]
  steam_raw (Docker)                          Limpeza/Normalização
  - JSONB completo                            - Extração de campos
  - Grande volume                             - Conversão de tipos
  - Histórico completo                        - Validação
       │                                             │
       │                                             ▼
       │                                      [DADOS LIMPOS]
       │                                      steam_bd (Supabase)
       │                                      - Campos estruturados
       │                                      - Otimizado para queries
       │                                      - Dashboard/Visualização
       │                                             │
       └─────────────────┬───────────────────────────┘
                         │
                         ▼
                  Análise e Previsão
                  (Modelos de ML)

┌─────────────────────────────────────────────────────────────────┐
│                    USO DAS CLASSES                              │
└─────────────────────────────────────────────────────────────────┘

PostgreSQL (psycopg2 direto)        SupabaseDB (API REST)
├─ steam_raw                        ├─ steam_bd
├─ itad_raw                         ├─ steam_generico
└─ Grande volume JSONB              └─ Dados normalizados

""")

print("\nTeste concluído! 🎉")
