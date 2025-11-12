"""
Teste dos Novos Métodos em PostgreSQL
======================================

Este script testa os métodos implementados:
1. buscar_appids_nao_processados() - AppIDs em steam_raw mas não em steam_bd
2. buscar_todos_appids() - Todos os AppIDs de uma tabela
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

# Configurar logging
Settings.configure_logging()

print("=" * 70)
print("TESTE DOS NOVOS MÉTODOS EM PostgreSQL")
print("=" * 70)

# Conectar ao banco
print("\n[1] Conectando ao banco Docker...")
PostgreSQL.conectar()
print("    ✓ Conectado!")

# Teste 1: Buscar todos os AppIDs de steam_raw
print("\n[2] Buscando todos os AppIDs em steam_raw...")
appids_raw = PostgreSQL.buscar_todos_appids("steam_raw")
print(f"    ✓ Total de AppIDs em steam_raw: {len(appids_raw)}")
if appids_raw:
    print(f"    → Primeiros 10: {appids_raw[:10]}")

# Teste 2: Buscar todos os AppIDs de steam_bd
print("\n[3] Buscando todos os AppIDs em steam_bd...")
appids_bd = PostgreSQL.buscar_todos_appids("steam_bd")
print(f"    ✓ Total de AppIDs em steam_bd: {len(appids_bd)}")
if appids_bd:
    print(f"    → Primeiros 10: {appids_bd[:10]}")

# Teste 3: Buscar AppIDs não processados
print("\n[4] Buscando AppIDs não processados (limite: 20)...")
appids_pendentes = PostgreSQL.buscar_appids_nao_processados(arg_intLimit=20)
print(f"    ✓ AppIDs que precisam ser processados: {len(appids_pendentes)}")
if appids_pendentes:
    print(f"    → AppIDs: {appids_pendentes}")

# Teste 4: Estatísticas
print("\n" + "=" * 70)
print("ESTATÍSTICAS")
print("=" * 70)
print(f"📦 Total em steam_raw:           {len(appids_raw):,} jogos")
print(f"🎮 Total em steam_bd:            {len(appids_bd):,} jogos")
print(f"⏳ Pendentes de processamento:   {len(appids_raw) - len(appids_bd):,} jogos")
print(f"✅ Taxa de processamento:        {(len(appids_bd)/len(appids_raw)*100):.2f}%" if appids_raw else "N/A")

# Teste 5: Verificar se nossos jogos de teste estão lá
print("\n[5] Verificando jogos de teste (888888, 999999)...")
for appid in [888888, 999999]:
    em_raw = appid in appids_raw
    em_bd = appid in appids_bd
    print(f"    AppID {appid}:")
    print(f"      - Em steam_raw: {'✓' if em_raw else '✗'}")
    print(f"      - Em steam_bd:  {'✓' if em_bd else '✗'}")
    print(f"      - Status: {'Processado' if em_bd else 'Pendente' if em_raw else 'Não encontrado'}")

# Desconectar
print("\n[6] Desconectando...")
PostgreSQL.desconectar()
print("    ✓ Desconectado!")

print("\n" + "=" * 70)
print("TESTE CONCLUÍDO COM SUCESSO! ✅")
print("=" * 70)
print("\n💡 Próximos passos:")
print("   1. Use buscar_appids_nao_processados() para obter jogos pendentes")
print("   2. Passe a lista para ProcessadorETL.processar_lote()")
print("   3. Os dados serão transformados e enviados ao Supabase!")
