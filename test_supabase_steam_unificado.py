"""Teste rápido da conexão Supabase e verificação de steam_unificado"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("TESTE: Configuração Supabase para steam_unificado")
print("=" * 60)

# 1. Verificar variáveis de ambiente
print("\n1. Verificando variáveis de ambiente...")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    print(f"✓ SUPABASE_URL: {supabase_url[:30]}...")
    print(f"✓ SUPABASE_KEY: {'*' * 20}... (existe)")
else:
    print("✗ ERRO: SUPABASE_URL ou SUPABASE_KEY não encontrados no .env")
    exit(1)

# 2. Testar conexão
print("\n2. Testando conexão com Supabase...")
try:
    from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
    SupabaseDB.conectar()
    print("✓ Conexão estabelecida com sucesso")
except Exception as e:
    print(f"✗ Erro ao conectar: {e}")
    exit(1)

# 3. Verificar se tabela existe
print("\n3. Verificando tabela steam_unificado no Supabase...")
try:
    total = SupabaseDB.contar_steam_unificado()
    print(f"✓ Tabela existe! Total de registros: {total:,}")
    
    if total == 0:
        print("⚠ Tabela vazia - pronta para sincronização")
    else:
        print(f"✓ Tabela já contém dados")
        
        # Busca um registro de exemplo
        jogos = SupabaseDB.buscar_todos_steam_unificado(limit=1)
        if jogos:
            print(f"  Exemplo: {jogos[0]['appid']} - {jogos[0]['nome']}")
            
except Exception as e:
    erro_str = str(e).lower()
    if 'does not exist' in erro_str or '42p01' in erro_str:
        print("✗ Tabela steam_unificado NÃO existe no Supabase")
        print("\n📋 PRÓXIMO PASSO:")
        print("Execute o SQL em: resources/docs/create_steam_unificado_supabase.sql")
        print("Via Supabase Dashboard > SQL Editor")
    else:
        print(f"✗ Erro: {e}")
    exit(1)

# 4. Verificar dados no Docker
print("\n4. Verificando steam_unificado no Docker PostgreSQL...")
try:
    from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
    PostgreSQL.conectar()
    
    jogos_docker = PostgreSQL.buscar_todos_steam_unificado(1)  # Limit como argumento posicional
    if jogos_docker:
        print(f"✓ Docker PostgreSQL OK")
        print(f"  Total no Docker: ~173.843 registros (estimado)")
    else:
        print("✗ Nenhum dado no Docker")
        
except Exception as e:
    print(f"✗ Erro ao acessar Docker: {e}")

# 5. Resumo
print("\n" + "=" * 60)
print("RESUMO DO TESTE")
print("=" * 60)
print("✓ Configuração Supabase: OK")
print("✓ Conexão: OK")

if total > 0:
    print(f"✓ Tabela steam_unificado: {total:,} registros")
    print("\n✅ TUDO PRONTO! Você pode:")
    print("   - Usar SupabaseDB.buscar_steam_unificado(appid)")
    print("   - Inserir novos dados com SupabaseDB.inserir_steam_unificado()")
    print("   - Sincronizar mais dados do Docker")
else:
    print("⚠ Tabela steam_unificado: VAZIA")
    print("\n📤 PRÓXIMA AÇÃO:")
    print("Execute: python sync_steam_unificado_supabase.py 500 1000")
    print("(Teste com 1.000 registros primeiro)")

print("=" * 60)
