"""
Script de teste para validar a lógica do supabase_db.py:
1. Insere DETALHES primeiro
2. Depois busca por APPID e adiciona REVIEWS
"""

import sys
import os
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

load_dotenv()

from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

def testar_insercao_sequencial():
    """
    Testa a lógica de inserção sequencial:
    1. Insere detalhes
    2. Busca por appid
    3. Adiciona reviews
    """
    
    print("=" * 60)
    print("🧪 TESTE: Inserção Sequencial de Detalhes e Reviews")
    print("=" * 60)
    
    try:
        # Conecta
        print("\n1️⃣ Conectando ao Supabase...")
        SupabaseDB.conectar()
        
        # AppID de teste
        appid_teste = 999999
        
        # PASSO 1: Inserir DETALHES primeiro
        print(f"\n2️⃣ Inserindo DETALHES para AppID {appid_teste}...")
        dados_detalhes = {
            "appid": appid_teste,
            "detalhes": {
                "name": "Jogo de Teste",
                "type": "game",
                "is_free": False,
                "developers": ["Desenvolvedor Teste"],
                "publishers": ["Publicador Teste"],
                "categories": [{"id": 1, "description": "Single-player"}],
                "genres": [{"id": 1, "description": "Action"}],
                "platforms": {"windows": True, "mac": False, "linux": False},
                "price_overview": {
                    "initial": 1999,
                    "final": 1499,
                    "discount_percent": 25
                },
                "release_date": {
                    "coming_soon": False,
                    "date": "1 Jan, 2024"
                }
            }
        }
        
        SupabaseDB.inserir_dadosSteamRaw(dados_detalhes)
        print("   ✅ Detalhes inseridos com sucesso!")
        
        # PASSO 2: Buscar por APPID
        print(f"\n3️⃣ Buscando registro por AppID {appid_teste}...")
        registro = SupabaseDB.buscar_dadosSteamRaw(appid_teste)
        
        if registro:
            print(f"   ✅ Registro encontrado!")
            print(f"   📦 AppID: {registro.get('appid')}")
            print(f"   📝 Tem detalhes: {'detalhes' in registro and registro['detalhes'] is not None}")
            print(f"   ⭐ Tem reviews: {'reviews' in registro and registro['reviews'] is not None}")
        else:
            print("   ❌ Registro não encontrado!")
            return False
        
        # PASSO 3: Adicionar REVIEWS ao registro existente
        print(f"\n4️⃣ Adicionando REVIEWS para AppID {appid_teste}...")
        dados_reviews = {
            "appid": appid_teste,
            "reviews": {
                "total_positive": 800,
                "total_negative": 200,
                "total_reviews": 1000,
                "review_score": 8,
                "review_score_desc": "Very Positive"
            }
        }
        
        SupabaseDB.inserir_dadosSteamRaw(dados_reviews)
        print("   ✅ Reviews adicionados com sucesso!")
        
        # PASSO 4: Verificar se ambos foram salvos
        print(f"\n5️⃣ Verificando registro final...")
        registro_final = SupabaseDB.buscar_dadosSteamRaw(appid_teste)
        
        if registro_final:
            tem_detalhes = 'detalhes' in registro_final and registro_final['detalhes'] is not None
            tem_reviews = 'reviews' in registro_final and registro_final['reviews'] is not None
            
            print(f"   📦 AppID: {registro_final.get('appid')}")
            print(f"   📝 Tem detalhes: {tem_detalhes}")
            print(f"   ⭐ Tem reviews: {tem_reviews}")
            
            if tem_detalhes and tem_reviews:
                print("\n   ✅ SUCESSO! Ambos detalhes e reviews foram salvos!")
                print(f"   🎮 Nome do jogo: {registro_final['detalhes'].get('name')}")
                print(f"   ⭐ Total de reviews: {registro_final['reviews'].get('total_reviews')}")
                return True
            else:
                print("\n   ❌ ERRO! Faltam dados:")
                if not tem_detalhes:
                    print("      - Detalhes não encontrados")
                if not tem_reviews:
                    print("      - Reviews não encontrados")
                return False
        else:
            print("   ❌ Registro final não encontrado!")
            return False
        
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Desconecta
        print("\n6️⃣ Desconectando...")
        SupabaseDB.desconectar()


def testar_warning_reviews_sem_detalhes():
    """
    Testa o aviso quando tenta adicionar reviews sem detalhes prévios
    """
    
    print("\n" + "=" * 60)
    print("🧪 TESTE: Aviso ao Inserir Reviews Sem Detalhes")
    print("=" * 60)
    
    try:
        # Conecta
        print("\n1️⃣ Conectando ao Supabase...")
        SupabaseDB.conectar()
        
        # AppID que não existe
        appid_inexistente = 888888
        
        # Tenta inserir REVIEWS sem ter inserido DETALHES antes
        print(f"\n2️⃣ Tentando inserir REVIEWS para AppID {appid_inexistente} (sem detalhes)...")
        dados_reviews = {
            "appid": appid_inexistente,
            "reviews": {
                "total_positive": 100,
                "total_negative": 50,
                "total_reviews": 150
            }
        }
        
        SupabaseDB.inserir_dadosSteamRaw(dados_reviews)
        print("   ⚠️ Deve ter mostrado um warning acima!")
        
        # Verifica se não foi criado registro
        print(f"\n3️⃣ Verificando se registro foi criado...")
        registro = SupabaseDB.buscar_dadosSteamRaw(appid_inexistente)
        
        if registro is None:
            print("   ✅ CORRETO! Registro não foi criado (esperado)")
            return True
        else:
            print("   ❌ ERRO! Registro foi criado sem detalhes")
            return False
        
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        return False
    
    finally:
        # Desconecta
        print("\n4️⃣ Desconectando...")
        SupabaseDB.desconectar()


def testar_estatisticas():
    """
    Testa o método de estatísticas
    """
    
    print("\n" + "=" * 60)
    print("🧪 TESTE: Obter Estatísticas")
    print("=" * 60)
    
    try:
        # Conecta
        print("\n1️⃣ Conectando ao Supabase...")
        SupabaseDB.conectar()
        
        # Obtém estatísticas
        print("\n2️⃣ Obtendo estatísticas...")
        stats = SupabaseDB.obter_estatisticas()
        
        print(f"\n   📊 ESTATÍSTICAS:")
        print(f"   📦 Total em steam_raw: {stats['total_raw']}")
        print(f"   🎮 Total em steam_bd: {stats['total_bd']}")
        print(f"   📈 Diferença: {stats['diferenca']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        return False
    
    finally:
        # Desconecta
        print("\n3️⃣ Desconectando...")
        SupabaseDB.desconectar()


if __name__ == "__main__":
    print("\n🚀 INICIANDO TESTES DO SUPABASE_DB\n")
    
    resultados = []
    
    # Teste 1: Inserção sequencial (detalhes → reviews)
    resultado1 = testar_insercao_sequencial()
    resultados.append(("Inserção Sequencial", resultado1))
    
    # Teste 2: Warning ao inserir reviews sem detalhes
    resultado2 = testar_warning_reviews_sem_detalhes()
    resultados.append(("Warning Reviews Sem Detalhes", resultado2))
    
    # Teste 3: Estatísticas
    resultado3 = testar_estatisticas()
    resultados.append(("Estatísticas", resultado3))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📋 RESUMO DOS TESTES")
    print("=" * 60)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    
    print(f"\n🎯 TOTAL: {passou}/{total} testes passaram")
    
    if passou == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️ Alguns testes falharam. Verifique os logs acima.")
