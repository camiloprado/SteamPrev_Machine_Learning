"""
Script de teste para verificar a conexão com o PostgreSQL na nuvem (Supabase).

Execute este script após configurar o arquivo .env com as credenciais do Supabase.
"""

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
import logging

logger = logging.getLogger(__name__)

def testar_conexao():
    """Testa a conexão com o banco de dados na nuvem."""
    try:
        logger.info("🔄 Testando conexão com o banco de dados...")
        PostgreSQL.conectar()
        logger.info("✅ Conexão estabelecida com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        return False

def testar_criacao_tabelas():
    """Testa a criação das tabelas."""
    try:
        logger.info("🔄 Criando tabelas...")
        PostgreSQL.criar_tabela_SteamRaw()
        PostgreSQL.criar_tabela_dadosSteam()
        logger.info("✅ Tabelas criadas com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        return False

def testar_insercao():
    """Testa a inserção de dados."""
    try:
        logger.info("🔄 Testando inserção de dados...")
        var_dictTeste = {
            "appid": 999999,
            "detalhes": {"teste": "conexao", "nome": "Jogo de Teste"},
            "reviews": {"total": 0}
        }
        PostgreSQL.inserir_dadosSteamRaw(var_dictTeste)
        logger.info("✅ Dados inseridos com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao inserir dados: {e}")
        return False

def testar_busca():
    """Testa a busca de dados."""
    try:
        logger.info("🔄 Testando busca de dados...")
        var_dictResultado = PostgreSQL.buscar_dados(999999, "steam_raw")
        if var_dictResultado:
            logger.info(f"✅ Dados recuperados com sucesso!")
            logger.info(f"   AppID: {var_dictResultado.get('appid')}")
            logger.info(f"   Detalhes: {var_dictResultado.get('detalhes')}")
            return True
        else:
            logger.warning("⚠️ Nenhum dado encontrado")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao buscar dados: {e}")
        return False

def executar_testes():
    """Executa todos os testes."""
    logger.info("=" * 60)
    logger.info("🧪 INICIANDO TESTES DE CONEXÃO COM POSTGRESQL NA NUVEM")
    logger.info("=" * 60)
    
    var_listTestes = [
        ("Conexão", testar_conexao),
        ("Criação de Tabelas", testar_criacao_tabelas),
        ("Inserção de Dados", testar_insercao),
        ("Busca de Dados", testar_busca)
    ]
    
    var_intPassou = 0
    var_intTotal = len(var_listTestes)
    
    for var_strNome, var_funcTeste in var_listTestes:
        logger.info("")
        logger.info(f"📋 Teste: {var_strNome}")
        logger.info("-" * 60)
        if var_funcTeste():
            var_intPassou += 1
        logger.info("-" * 60)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"📊 RESULTADO: {var_intPassou}/{var_intTotal} testes passaram")
    logger.info("=" * 60)
    
    if var_intPassou == var_intTotal:
        logger.info("🎉 Todos os testes passaram! Banco de dados na nuvem funcionando perfeitamente!")
    else:
        logger.warning(f"⚠️ {var_intTotal - var_intPassou} teste(s) falharam. Verifique o arquivo .env e as credenciais do Supabase.")
    
    # Desconectar
    try:
        PostgreSQL.desconectar()
        logger.info("🔌 Conexão encerrada.")
    except:
        pass

if __name__ == "__main__":
    executar_testes()
