"""
Teste de correções no ProcessadorETL:
1. Normalização de gêneros (a????o -> Acao)
2. Conversão de datas para formato ISO (1/Nov/2000 -> 2000-11-01)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL

def test_processar_generos():
    """
    Testa normalização de gêneros
    """
    print("=" * 70)
    print("TESTE 1: Normalização de Gêneros")
    print("=" * 70)
    
    # Casos de teste
    var_listTestes = [
        # (Entrada, Saída Esperada)
        (
            [{"description": "a????o"}],
            ["Acao"]
        ),
        (
            [{"description": "Ação"}, {"description": "Aventura"}],
            ["Acao", "Aventura"]
        ),
        (
            [{"description": "RPG"}, {"description": "Estratégia"}, {"description": "Simulação"}],
            ["RPG", "Estrategia", "Simulacao"]
        ),
        (
            [{"description": "Corrida"}, {"description": "Esportes"}],
            ["Corrida", "Esportes"]
        ),
    ]
    
    print("\n📋 Testando processamento de gêneros:\n")
    
    var_intSucessos = 0
    var_intFalhas = 0
    
    for var_listEntrada, var_listEsperado in var_listTestes:
        var_listResultado = ProcessadorETL.processar_generos(var_listEntrada)
        var_boolSucesso = var_listResultado == var_listEsperado
        
        if var_boolSucesso:
            var_intSucessos += 1
            print(f"✓ {var_listEntrada} → {var_listResultado}")
        else:
            var_intFalhas += 1
            print(f"✗ {var_listEntrada}")
            print(f"  Resultado: {var_listResultado}")
            print(f"  Esperado: {var_listEsperado}")
    
    print("\n" + "-" * 70)
    print(f"Resultados: {var_intSucessos} sucessos, {var_intFalhas} falhas")
    print("=" * 70)

def test_processar_data_lancamento():
    """
    Testa conversão de datas para formato ISO
    """
    print("\n" + "=" * 70)
    print("TESTE 2: Conversão de Datas para Formato ISO")
    print("=" * 70)
    
    # Casos de teste
    var_listTestes = [
        # (Entrada, Saída Esperada)
        ("1 Nov, 2000", "2000-11-01"),
        ("Nov 1, 2000", "2000-11-01"),
        ("1/Nov/2000", "2000-11-01"),
        ("2000-11-01", "2000-11-01"),
        ("15 Dec, 2023", "2023-12-15"),
        ("December 15, 2023", "2023-12-15"),
        ("01/05/2020", "2020-01-05"),  # Pode ser ambíguo
        ("2020-05-15", "2020-05-15"),
        ("", ""),
        ("Invalid Date", ""),
    ]
    
    print("\n📋 Testando conversão de datas:\n")
    
    var_intSucessos = 0
    var_intFalhas = 0
    
    for var_strEntrada, var_strEsperado in var_listTestes:
        var_strResultado = ProcessadorETL.processar_data_lancamento(var_strEntrada)
        var_boolSucesso = var_strResultado == var_strEsperado
        
        if var_boolSucesso:
            var_intSucessos += 1
            print(f"✓ '{var_strEntrada}' → '{var_strResultado}'")
        else:
            var_intFalhas += 1
            print(f"✗ '{var_strEntrada}'")
            print(f"  Resultado: '{var_strResultado}'")
            print(f"  Esperado: '{var_strEsperado}'")
    
    print("\n" + "-" * 70)
    print(f"Resultados: {var_intSucessos} sucessos, {var_intFalhas} falhas")
    print("=" * 70)

def test_transformacao_completa():
    """
    Testa transformação completa com dados simulados
    """
    print("\n" + "=" * 70)
    print("TESTE 3: Transformação Completa de Dados")
    print("=" * 70)
    
    # Dados simulados da Steam
    var_dictDadosRaw = {
        "steam_appid": 123456,
        "appid": 123456,
        "detalhes": {
            "name": "Jogo de Teste",
            "required_age": 18,
            "supported_languages": "Português-Brasil, Ingl??s, Alem??o",
            "developers": ["Dev A", "Dev B"],
            "publishers": ["Publisher A"],
            "price_overview": {
                "currency": "BRL",
                "final": 4999
            },
            "metacritic": {
                "score": 85
            },
            "categories": [
                {"description": "Single-player"},
                {"description": "Multi-player"}
            ],
            "genres": [
                {"description": "Ação"},
                {"description": "a????o"},
                {"description": "Aventura"}
            ],
            "release_date": {
                "date": "1 Nov, 2000"
            }
        },
        "reviews": {
            "review_score": 8,
            "total_reviews": 1000,
            "total_negative": 200,
            "total_positive": 800,
            "review_score_desc": "Very Positive"
        }
    }
    
    print("\n📋 Dados de Entrada (RAW):")
    print(f"  Gêneros: {[g['description'] for g in var_dictDadosRaw['detalhes']['genres']]}")
    print(f"  Data: {var_dictDadosRaw['detalhes']['release_date']['date']}")
    print(f"  Linguagens: {var_dictDadosRaw['detalhes']['supported_languages']}")
    
    # Processa
    var_dictDadosProcessados = ProcessadorETL.transformar_raw_para_bd(var_dictDadosRaw)
    
    print("\n✅ Dados de Saída (ESTRUTURADOS):")
    print(f"  AppID: {var_dictDadosProcessados['appid']}")
    print(f"  Nome: {var_dictDadosProcessados['nome']}")
    print(f"  Gêneros: {var_dictDadosProcessados['genero']}")
    print(f"  Data Lançamento: {var_dictDadosProcessados['data_lancamento']}")
    print(f"  Linguagens: {var_dictDadosProcessados['linguagens']}")
    print(f"  Preço: {var_dictDadosProcessados['preco']}")
    print(f"  Metacritic: {var_dictDadosProcessados['metacritic_score']}")
    print(f"  Review Score: {var_dictDadosProcessados['review_score']}")
    
    print("\n🔍 Verificações:")
    
    # Verifica gêneros
    if "Acao" in var_dictDadosProcessados['genero']:
        print("  ✓ Gênero 'Ação' foi normalizado para 'Acao'")
    else:
        print("  ✗ ERRO: Gênero 'Ação' não foi normalizado corretamente")
    
    # Verifica duplicatas
    if var_dictDadosProcessados['genero'].count("Acao") <= 1:
        print("  ✓ Sem duplicatas de gênero")
    else:
        print("  ⚠ ATENÇÃO: Gênero 'Acao' aparece múltiplas vezes")
    
    # Verifica data
    if var_dictDadosProcessados['data_lancamento'] == "2000-11-01":
        print("  ✓ Data convertida para formato ISO: 2000-11-01")
    else:
        print(f"  ✗ ERRO: Data não convertida corretamente: {var_dictDadosProcessados['data_lancamento']}")
    
    # Verifica linguagens
    if "Ingles" in var_dictDadosProcessados['linguagens']:
        print("  ✓ Linguagens normalizadas (Ingl??s → Ingles)")
    else:
        print("  ✗ ERRO: Linguagens não normalizadas corretamente")
    
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_processar_generos()
        test_processar_data_lancamento()
        test_transformacao_completa()
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS!\n")
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
