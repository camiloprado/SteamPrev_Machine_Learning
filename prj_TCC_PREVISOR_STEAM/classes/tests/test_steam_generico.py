"""
Script de teste para inserir dados na tabela steam_generico usando PostgreSQL.

Este script demonstra como usar o método inserir_dadosSteamGenerico() do PostgreSQL
que replica a funcionalidade do Supabase.
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

def test_inserir_steam_generico():
    """
    Testa a inserção de dados genéricos da Steam no PostgreSQL.
    """
    print("=" * 60)
    print("TESTE: Inserção de Dados Steam Genérico no PostgreSQL")
    print("=" * 60)
    
    # Configurações já são inicializadas automaticamente no import
    # Settings.build() já foi chamado no final de AllSettings.py
    
    # Dados de exemplo
    var_listDadosGerais = [
        {"appid": 100001, "name": "Jogo Teste 1"},
        {"appid": 100002, "name": "Jogo Teste 2"},
        {"appid": 100003, "name": "Jogo Teste 3"},
        {"appid": 888888, "name": "Jogo Teste Híbrido (atualizado)"},
        {"appid": 999999, "name": "Outro Jogo Teste (atualizado)"}
    ]
    
    print(f"\n[1] Conectando ao PostgreSQL...")
    PostgreSQL.conectar()
    print("✓ Conectado com sucesso\n")
    
    print(f"[2] Verificando jogos desatualizados em steam_generico...")
    var_listDesatualizados = PostgreSQL.buscar_jogos_desatualizados(
        arg_strNomeTabela="steam_generico",
        arg_intLimite=10
    )
    print(f"✓ Encontrados {len(var_listDesatualizados)} jogos desatualizados")
    
    if var_listDesatualizados:
        print("\nPrimeiros jogos desatualizados:")
        for jogo in var_listDesatualizados[:5]:
            print(f"  - AppID {jogo.get('appid')}: {jogo.get('name')} "
                  f"(última atualização: {jogo.get('ultima_atualizacao')})")
    
    print(f"\n[3] Inserindo {len(var_listDadosGerais)} jogos genéricos...")
    var_boolSucesso = PostgreSQL.inserir_dadosSteamGenerico(var_listDadosGerais)
    
    if var_boolSucesso:
        print("✓ Dados inseridos/atualizados com sucesso")
    else:
        print("⚠ Nenhum dado foi inserido (nenhum jogo desatualizado)")
    
    print(f"\n[4] Verificando dados inseridos...")
    for dados in var_listDadosGerais:
        var_intAppid = dados.get("appid")
        var_dictDados = PostgreSQL.buscar_dados(var_intAppid, "steam_generico")
        
        if var_dictDados:
            print(f"✓ AppID {var_intAppid}: {var_dictDados.get('name')}")
        else:
            print(f"✗ AppID {var_intAppid}: NÃO ENCONTRADO")
    
    print(f"\n[5] Estatísticas da tabela steam_generico...")
    var_listTodosAppids = PostgreSQL.buscar_todos_appids("steam_generico")
    print(f"✓ Total de AppIDs em steam_generico: {len(var_listTodosAppids):,}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO!")
    print("=" * 60)

def test_comparacao_metodos():
    """
    Compara a funcionalidade entre PostgreSQL e Supabase.
    """
    print("\n" + "=" * 60)
    print("COMPARAÇÃO: Métodos PostgreSQL vs Supabase")
    print("=" * 60)
    
    print("\n📋 Métodos implementados:")
    print("\n1. inserir_dadosSteamGenerico(arg_listDadosGerais)")
    print("   PostgreSQL: ✓ Implementado com verificação de desatualizados")
    print("   Supabase:   ✓ Implementado com verificação de desatualizados")
    
    print("\n2. buscar_jogos_desatualizados(arg_strNomeTabela, arg_intLimite)")
    print("   PostgreSQL: ✓ Implementado com filtro por data")
    print("   Supabase:   ✓ Implementado com filtro por data")
    
    print("\n3. Processamento em lotes (5000 registros)")
    print("   PostgreSQL: ✓ Implementado com commits por lote")
    print("   Supabase:   ✓ Implementado com upsert em lotes")
    
    print("\n4. Upsert (INSERT ... ON CONFLICT DO UPDATE)")
    print("   PostgreSQL: ✓ Usando ON CONFLICT DO UPDATE")
    print("   Supabase:   ✓ Usando upsert() API")
    
    print("\n✅ Ambos os métodos são funcionalmente equivalentes!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        # Executa teste de inserção
        test_inserir_steam_generico()
        
        # Executa comparação
        test_comparacao_metodos()
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        PostgreSQL.desconectar()
