"""
Script de teste para a API REST do Supabase.

Este script testa todas as funcionalidades da classe SupabaseDB.
"""

from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
import logging

logger = logging.getLogger(__name__)


def testar_conexao():
    """Testa a conexão com o Supabase via API REST."""
    try:
        logger.info("🔄 Testando conexão com Supabase API...")
        SupabaseDB.conectar()
        logger.info("✅ Conexão estabelecida!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def testar_insercao_raw():
    """Testa inserção na tabela steam_raw."""
    try:
        logger.info("🔄 Testando inserção em steam_raw...")
        var_dictDados = {
            "appid": 888888,
            "detalhes": {
                "nome": "Jogo Teste API",
                "desenvolvedores": ["Test Studio"]
            },
            "reviews": {
                "total": 100,
                "positivo": 80
            }
        }
        var_dictResultado = SupabaseDB.inserir_dadosSteamRaw(var_dictDados)
        logger.info(f"✅ Inserido: {var_dictResultado}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def testar_busca_raw():
    """Testa busca na tabela steam_raw."""
    try:
        logger.info("🔄 Testando busca em steam_raw...")
        var_dictDados = SupabaseDB.buscar_dadosSteamRaw(888888)
        if var_dictDados:
            logger.info(f"✅ Encontrado: AppID {var_dictDados.get('appid')}")
            return True
        else:
            logger.warning("⚠️ Nenhum dado encontrado")
            return False
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def testar_insercao_bd():
    """Testa inserção na tabela steam_bd."""
    try:
        logger.info("🔄 Testando inserção em steam_bd...")
        var_dictDados = {
            "appid": 888888,
            "nome": "Jogo Teste API",
            "idade_classificada": "18+",
            "classificacao_etaria": "Mature",
            "linguagens": ["English", "Portuguese"],
            "desenvolvedores": ["Test Studio"],
            "distribuidores": ["Test Publisher"],
            "preco": "R$ 49,99",
            "metacritic_score": "85",
            "categorias": ["Action", "Adventure"],
            "genero": ["RPG", "Open World"],
            "data_lancamento": "2025-01-01",
            "reviews": {"total": 100, "positivo": 80}
        }
        var_dictResultado = SupabaseDB.inserir_dadosSteamBD(var_dictDados)
        logger.info(f"✅ Inserido: {var_dictResultado}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def testar_busca_por_nome():
    """Testa busca por nome."""
    try:
        logger.info("🔄 Testando busca por nome...")
        var_listResultados = SupabaseDB.buscar_jogos_por_nome("Teste")
        logger.info(f"✅ Encontrados: {len(var_listResultados)} jogos")
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def testar_estatisticas():
    """Testa obtenção de estatísticas."""
    try:
        logger.info("🔄 Testando estatísticas...")
        var_dictStats = SupabaseDB.obter_estatisticas()
        logger.info(f"✅ Stats: {var_dictStats}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def executar_testes():
    """Executa todos os testes."""
    logger.info("=" * 70)
    logger.info("🧪 TESTES DA API REST DO SUPABASE")
    logger.info("=" * 70)
    
    var_listTestes = [
        ("Conexão", testar_conexao),
        ("Inserção steam_raw", testar_insercao_raw),
        ("Busca steam_raw", testar_busca_raw),
        ("Inserção steam_bd", testar_insercao_bd),
        ("Busca por nome", testar_busca_por_nome),
        ("Estatísticas", testar_estatisticas)
    ]
    
    var_intPassou = 0
    var_intTotal = len(var_listTestes)
    
    for var_strNome, var_funcTeste in var_listTestes:
        logger.info("")
        logger.info(f"📋 Teste: {var_strNome}")
        logger.info("-" * 70)
        if var_funcTeste():
            var_intPassou += 1
        logger.info("-" * 70)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"📊 RESULTADO: {var_intPassou}/{var_intTotal} testes passaram")
    logger.info("=" * 70)
    
    if var_intPassou == var_intTotal:
        logger.info("🎉 Todos os testes passaram!")
    else:
        logger.warning(f"⚠️ {var_intTotal - var_intPassou} teste(s) falharam")
    
    # Desconectar
    SupabaseDB.desconectar()


if __name__ == "__main__":
    executar_testes()
