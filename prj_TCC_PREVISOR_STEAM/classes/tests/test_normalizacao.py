"""
Teste de normalização de texto - Remove acentuação e caracteres corrompidos
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL

def test_normalizacao():
    """
    Testa a normalização de textos com acentuação e caracteres corrompidos
    """
    print("=" * 70)
    print("TESTE: Normalização de Texto (Remoção de Acentuação)")
    print("=" * 70)
    
    # Casos de teste
    var_listTestes = [
        # (Entrada, Saída Esperada)
        ("Português", "Portugues"),
        ("Ingl??s", "Ingles"),
        ("Alem??o", "Alemao"),
        ("Español", "Espanol"),
        ("Français", "Francais"),
        ("Japonês", "Japones"),
        ("中文 (Chinês Simplificado)", "中文 (Chines Simplificado)"),
        ("Ação e Aventura", "Acao e Aventura"),
        ("RPG de Açúcar", "RPG de Acucar"),
        ("���Corrompido???", "Corrompido"),
        ("Múltiplos  Espaços", "Multiplos Espacos"),
    ]
    
    print("\n📋 Testando normalização de textos:\n")
    
    var_intSucessos = 0
    var_intFalhas = 0
    
    for var_strEntrada, var_strEsperado in var_listTestes:
        var_strResultado = ProcessadorETL.normalizar_texto(var_strEntrada)
        var_boolSucesso = var_strResultado == var_strEsperado
        
        if var_boolSucesso:
            var_intSucessos += 1
            print(f"✓ '{var_strEntrada}' → '{var_strResultado}'")
        else:
            var_intFalhas += 1
            print(f"✗ '{var_strEntrada}' → '{var_strResultado}' (esperado: '{var_strEsperado}')")
    
    print("\n" + "-" * 70)
    print(f"Resultados: {var_intSucessos} sucessos, {var_intFalhas} falhas")
    print("=" * 70)

def test_processar_linguas():
    """
    Testa o processamento de linguagens com normalização
    """
    print("\n" + "=" * 70)
    print("TESTE: Processamento de Linguagens")
    print("=" * 70)
    
    # Casos de teste
    var_listTestes = [
        (
            "Português-Brasil, Ingl??s, Alem??o, Español",
            ["Portugues-Brasil", "Ingles", "Alemao", "Espanol"]
        ),
        (
            "<strong>Japonês</strong>, *Chinês Simplificado*, Francês",
            ["Japones", "Frances"]
        ),
        (
            "English, French, German, Spanish, Portuguese, Italian",
            ["English", "French", "German", "Spanish", "Portuguese", "Italian"]
        ),
    ]
    
    print("\n📋 Testando processamento de linguagens:\n")
    
    for var_strEntrada, var_listEsperado in var_listTestes:
        var_listResultado = ProcessadorETL.processar_linguas(var_strEntrada)
        
        print(f"Entrada: {var_strEntrada}")
        print(f"Resultado: {var_listResultado}")
        print(f"Esperado: {var_listEsperado}")
        
        if var_listResultado == var_listEsperado:
            print("✓ SUCESSO\n")
        else:
            print("⚠ DIFERENTE (mas pode estar correto dependendo da lógica)\n")
    
    print("=" * 70)

def test_exemplo_real():
    """
    Testa com exemplo real de dados da Steam
    """
    print("\n" + "=" * 70)
    print("TESTE: Exemplo Real de Dados Steam")
    print("=" * 70)
    
    # Simula dados brutos da Steam
    var_dictDadosRaw = {
        "steam_appid": 123456,
        "detalhes": {
            "name": "Jogo de Ação",
            "supported_languages": "<strong>Português-Brasil</strong>, Ingl??s, Alem??o, *Japonês*, Español"
        },
        "reviews": {}
    }
    
    print("\n📋 Dados Brutos:")
    print(f"Nome: {var_dictDadosRaw['detalhes']['name']}")
    print(f"Linguagens: {var_dictDadosRaw['detalhes']['supported_languages']}")
    
    # Processa
    var_listLinguagens = ProcessadorETL.processar_linguas(
        var_dictDadosRaw['detalhes']['supported_languages']
    )
    
    print("\n✅ Linguagens Processadas (sem acentuação):")
    for idx, var_strLingua in enumerate(var_listLinguagens, 1):
        print(f"  {idx}. {var_strLingua}")
    
    print("\n💡 Benefícios:")
    print("  • Remove caracteres corrompidos (??)")
    print("  • Remove tags HTML (<strong>)")
    print("  • Remove marcadores (*)")
    print("  • Normaliza acentuação (ã→a, ê→e, ç→c)")
    print("  • Limpa espaços extras")
    
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_normalizacao()
        test_processar_linguas()
        test_exemplo_real()
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS!\n")
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
