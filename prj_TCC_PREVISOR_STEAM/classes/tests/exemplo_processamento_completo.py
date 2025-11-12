"""
Exemplo Completo: Processamento Docker → Supabase
==================================================

Este script demonstra o fluxo completo de processamento usando
a arquitetura híbrida implementada.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

# Configurar logging
Settings.configure_logging()

print("=" * 70)
print("PROCESSAMENTO COMPLETO: Docker → Supabase")
print("=" * 70)

# PASSO 1: Verificar quantos jogos precisam ser processados
print("\n[PASSO 1] Verificando jogos pendentes...")
appids_pendentes = PostgreSQL.buscar_appids_nao_processados(arg_intLimit=10)

if not appids_pendentes:
    print("  ✓ Nenhum jogo pendente de processamento!")
    print("  → Todos os jogos em steam_raw já foram processados para steam_bd")
    exit(0)

print(f"  → Encontrados {len(appids_pendentes)} jogos pendentes")
print(f"  → AppIDs a processar: {appids_pendentes[:5]}{'...' if len(appids_pendentes) > 5 else ''}")

# PASSO 2: Processar os jogos pendentes
print("\n[PASSO 2] Processando jogos...")
print(f"  → Transformando dados RAW (Docker) em dados ESTRUTURADOS (Supabase)")

try:
    ProcessadorETL.processar_lote(appids_pendentes)
    print("  ✓ Processamento concluído com sucesso!")
except Exception as e:
    print(f"  ✗ Erro durante processamento: {e}")
    exit(1)

# PASSO 3: Verificar resultados
print("\n[PASSO 3] Verificando resultados...")
appids_ainda_pendentes = PostgreSQL.buscar_appids_nao_processados(arg_intLimit=10)

jogos_processados = len(appids_pendentes) - len(appids_ainda_pendentes)
print(f"  ✓ {jogos_processados} jogos processados nesta execução")

# PASSO 4: Estatísticas finais
print("\n" + "=" * 70)
print("ESTATÍSTICAS FINAIS")
print("=" * 70)

total_raw = len(PostgreSQL.buscar_todos_appids("steam_raw"))
total_bd = len(PostgreSQL.buscar_todos_appids("steam_bd"))
pendentes = total_raw - total_bd

print(f"📦 Total em steam_raw (Docker):     {total_raw:,} jogos")
print(f"🎮 Total em steam_bd (Supabase):    {total_bd:,} jogos")
print(f"⏳ Ainda pendentes:                 {pendentes:,} jogos")
print(f"✅ Taxa de conclusão:               {(total_bd/total_raw*100):.2f}%")

print("\n" + "=" * 70)
print("PROCESSAMENTO CONCLUÍDO! 🎉")
print("=" * 70)

print("\n💡 Para processar TODOS os jogos pendentes:")
print("   while True:")
print("       appids = PostgreSQL.buscar_appids_nao_processados(1000)")
print("       if not appids:")
print("           break")
print("       ProcessadorETL.processar_lote(appids)")
