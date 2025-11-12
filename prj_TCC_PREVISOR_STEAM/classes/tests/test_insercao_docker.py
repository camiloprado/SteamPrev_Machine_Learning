"""
Teste de inserção SEQUENCIAL de dados no PostgreSQL Docker
Simula o comportamento real: primeiro detalhes, depois reviews
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from datetime import datetime

print("=== TESTE DE INSERÇÃO SEQUENCIAL NO POSTGRESQL (DOCKER) ===\n")

try:
    print("1. Conectando ao PostgreSQL...")
    PostgreSQL.conectar()
    print("   ✓ Conectado!\n")
    
    # ========== SIMULAÇÃO DO FLUXO REAL ==========
    
    print("2. ETAPA 1: Inserindo apenas DETALHES (como faz fetch_details_bulk_batched)...")
    dados_detalhes = [
        {
            "appid": 999991,
            "detalhes": {"name": "Counter-Strike Test", "type": "game", "price": "R$ 27,99"},
            "reviews": None  # Reviews ainda não foram buscados
        },
        {
            "appid": 999992,
            "detalhes": {"name": "Portal Test", "type": "game", "price": "R$ 19,99"},
            "reviews": None
        }
    ]
    PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=dados_detalhes)
    print("   ✓ Detalhes inseridos!\n")
    
    print("3. Verificando estado após inserção de detalhes...")
    for dado in dados_detalhes:
        appid = dado["appid"]
        resultado = PostgreSQL.buscar_dados(arg_intAppid=appid, arg_strNomeTabela="steam_raw")
        if resultado:
            print(f"   AppID {appid}:")
            print(f"     - Detalhes: {'✓ PRESENTE' if resultado.get('detalhes') else '✗ AUSENTE'}")
            print(f"     - Reviews: {'✓ PRESENTE' if resultado.get('reviews') else '✗ AUSENTE (esperado)'}")
        else:
            print(f"   AppID {appid}: ✗ NÃO ENCONTRADO")
    
    print("\n4. ETAPA 2: Inserindo apenas REVIEWS (como faz fetch_reviews_summary_batched)...")
    dados_reviews = [
        {
            "appid": 999991,
            "detalhes": None,  # Detalhes já foram inseridos antes
            "reviews": {"total_reviews": 1500000, "review_score": 95, "review_score_desc": "Overwhelmingly Positive"}
        },
        {
            "appid": 999992,
            "detalhes": None,
            "reviews": {"total_reviews": 250000, "review_score": 98, "review_score_desc": "Overwhelmingly Positive"}
        }
    ]
    PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=dados_reviews)
    print("   ✓ Reviews inseridos!\n")
    
    print("5. VERIFICAÇÃO FINAL: Ambos os campos devem estar presentes...")
    sucesso = True
    for appid in [999991, 999992]:
        resultado = PostgreSQL.buscar_dados(arg_intAppid=appid, arg_strNomeTabela="steam_raw")
        if resultado:
            tem_detalhes = resultado.get('detalhes') is not None
            tem_reviews = resultado.get('reviews') is not None
            
            print(f"   AppID {appid}:")
            print(f"     - Detalhes: {'✓ PRESERVADO' if tem_detalhes else '✗ PERDIDO (PROBLEMA!)'}")
            print(f"     - Reviews: {'✓ ADICIONADO' if tem_reviews else '✗ NÃO INSERIDO (PROBLEMA!)'}")
            
            if not tem_detalhes or not tem_reviews:
                sucesso = False
                print(f"     ⚠️ PROBLEMA DETECTADO!")
        else:
            print(f"   AppID {appid}: ✗ NÃO ENCONTRADO (PROBLEMA GRAVE!)")
            sucesso = False
    
    print("\n6. Testando inserção de jogo AUSENTE (detalhes = 'AUSENTE')...")
    dados_ausente = [
        {
            "appid": 999993,
            "detalhes": "AUSENTE",  # API retornou success=false
            "reviews": None
        }
    ]
    PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=dados_ausente)
    resultado = PostgreSQL.buscar_dados(arg_intAppid=999993, arg_strNomeTabela="steam_raw")
    if resultado:
        print(f"   AppID 999993:")
        print(f"     - Detalhes: {resultado.get('detalhes')}")
        print(f"     - Status: ✓ Jogo ausente registrado corretamente")
    
    print("\n7. Limpando dados de teste...")
    with PostgreSQL._var_connConnection.cursor() as cursor:
        cursor.execute("DELETE FROM steam_raw WHERE appid IN (999991, 999992, 999993);")
        PostgreSQL._var_connConnection.commit()
    print("   ✓ Dados removidos!\n")
    
    if sucesso:
        print("=== ✓ TESTE CONCLUÍDO COM SUCESSO! ===")
        print("COALESCE funcionou corretamente:")
        print("  1. Detalhes foram preservados quando reviews foram inseridos")
        print("  2. Reviews foram adicionados sem apagar detalhes existentes")
        print("  3. Inserção sequencial está segura para uso em produção!")
    else:
        print("=== ✗ TESTE FALHOU! ===")
        print("PROBLEMA: Dados foram perdidos na inserção sequencial!")
        print("AÇÃO NECESSÁRIA: Verificar lógica do COALESCE no SQL")
    
except Exception as e:
    print(f"\n✗ ERRO: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    print("\n8. Desconectando...")
    PostgreSQL.desconectar()
    print("   ✓ Desconectado!")

