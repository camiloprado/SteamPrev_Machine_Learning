"""
Script para migrar dados do PostgreSQL local para o Supabase (nuvem).

Este script:
1. Conecta ao banco LOCAL
2. Exporta todos os dados das tabelas steam_raw e steam_bd
3. Conecta ao banco NUVEM (Supabase)
4. Importa todos os dados

IMPORTANTE: Configure as credenciais corretas no .env antes de executar!
"""

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
import logging
import os

logger = logging.getLogger(__name__)

def migrar_dados():
    """Migra dados do PostgreSQL local para o Supabase."""
    
    logger.info("=" * 70)
    logger.info("🔄 INICIANDO MIGRAÇÃO DE DADOS - LOCAL → SUPABASE")
    logger.info("=" * 70)
    
    # ========================================
    # PASSO 1: Exportar dados do banco LOCAL
    # ========================================
    logger.info("")
    logger.info("📦 PASSO 1: Exportando dados do banco LOCAL...")
    logger.info("-" * 70)
    
    # Salvar credenciais atuais do Supabase
    var_strSupabaseHost = os.getenv("DB_HOST")
    var_strSupabaseUser = os.getenv("DB_USER")
    var_strSupabasePassword = os.getenv("DB_PASSWORD")
    var_strSupabasePort = os.getenv("DB_PORT")
    var_strSupabaseName = os.getenv("DB_NAME")
    
    # As credenciais locais já foram configuradas via input do usuário
    # Não precisamos alterar os.environ aqui pois já foi feito no __main__
    
    var_listDadosRaw = []
    var_listDadosBD = []
    
    try:
        logger.info("🔌 Conectando ao banco LOCAL...")
        PostgreSQL.conectar()
        logger.info("✅ Conectado ao banco LOCAL!")
        
        # Exportar steam_raw
        logger.info("📥 Exportando dados da tabela 'steam_raw'...")
        try:
            var_listDadosRaw = PostgreSQL.buscar_todos_dados("steam_raw")
            logger.info(f"✅ {len(var_listDadosRaw)} registros exportados de 'steam_raw'")
        except Exception as e:
            logger.warning(f"⚠️ Tabela 'steam_raw' não encontrada ou vazia: {e}")
        
        # Exportar steam_bd
        logger.info("📥 Exportando dados da tabela 'steam_bd'...")
        try:
            var_listDadosBD = PostgreSQL.buscar_todos_dados("steam_bd")
            logger.info(f"✅ {len(var_listDadosBD)} registros exportados de 'steam_bd'")
        except Exception as e:
            logger.warning(f"⚠️ Tabela 'steam_bd' não encontrada ou vazia: {e}")
        
        PostgreSQL.desconectar()
        logger.info("🔌 Desconectado do banco LOCAL")
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar/exportar do banco LOCAL: {e}")
        logger.error("💡 Verifique se:")
        logger.error("   - O PostgreSQL local está rodando")
        logger.error("   - As credenciais locais estão corretas no script")
        logger.error("   - O banco 'previsao_steam' existe")
        return
    
    # ========================================
    # PASSO 2: Verificar se há dados para migrar
    # ========================================
    var_intTotalRegistros = len(var_listDadosRaw) + len(var_listDadosBD)
    
    if var_intTotalRegistros == 0:
        logger.warning("")
        logger.warning("⚠️ NENHUM DADO ENCONTRADO PARA MIGRAR!")
        logger.warning("O banco local está vazio ou as tabelas não existem.")
        logger.warning("")
        return
    
    logger.info("")
    logger.info(f"📊 RESUMO DA EXPORTAÇÃO:")
    logger.info(f"   - steam_raw: {len(var_listDadosRaw)} registros")
    logger.info(f"   - steam_bd: {len(var_listDadosBD)} registros")
    logger.info(f"   - TOTAL: {var_intTotalRegistros} registros")
    
    # ========================================
    # PASSO 3: Importar dados para o SUPABASE
    # ========================================
    logger.info("")
    logger.info("☁️ PASSO 2: Importando dados para o SUPABASE...")
    logger.info("-" * 70)
    
    # Restaurar credenciais do Supabase
    logger.info("⚙️ Configurando conexão com SUPABASE...")
    os.environ["DB_HOST"] = var_strSupabaseHost
    os.environ["DB_USER"] = var_strSupabaseUser
    os.environ["DB_PASSWORD"] = var_strSupabasePassword
    os.environ["DB_PORT"] = var_strSupabasePort
    os.environ["DB_NAME"] = var_strSupabaseName
    
    try:
        logger.info("🔌 Conectando ao SUPABASE...")
        PostgreSQL.conectar()
        logger.info("✅ Conectado ao SUPABASE!")
        
        # Importar steam_raw
        if var_listDadosRaw:
            logger.info("")
            logger.info(f"📤 Importando {len(var_listDadosRaw)} registros para 'steam_raw'...")
            var_intSucessoRaw = 0
            var_intErroRaw = 0
            
            for idx, var_dictDado in enumerate(var_listDadosRaw, 1):
                try:
                    PostgreSQL.inserir_dadosSteamRaw(var_dictDado)
                    var_intSucessoRaw += 1
                    
                    # Log de progresso a cada 100 registros
                    if idx % 100 == 0:
                        logger.info(f"   Progresso: {idx}/{len(var_listDadosRaw)} ({idx/len(var_listDadosRaw)*100:.1f}%)")
                except Exception as e:
                    var_intErroRaw += 1
                    logger.warning(f"   ⚠️ Erro ao inserir AppID {var_dictDado.get('appid')}: {e}")
            
            logger.info(f"✅ steam_raw: {var_intSucessoRaw} inseridos, {var_intErroRaw} erros")
        
        # Importar steam_bd
        if var_listDadosBD:
            logger.info("")
            logger.info(f"📤 Importando {len(var_listDadosBD)} registros para 'steam_bd'...")
            var_intSucessoBD = 0
            var_intErroBD = 0
            
            for idx, var_dictDado in enumerate(var_listDadosBD, 1):
                try:
                    PostgreSQL.inserir_dadosSteamBD(var_dictDado)
                    var_intSucessoBD += 1
                    
                    # Log de progresso a cada 100 registros
                    if idx % 100 == 0:
                        logger.info(f"   Progresso: {idx}/{len(var_listDadosBD)} ({idx/len(var_listDadosBD)*100:.1f}%)")
                except Exception as e:
                    var_intErroBD += 1
                    logger.warning(f"   ⚠️ Erro ao inserir AppID {var_dictDado.get('appid')}: {e}")
            
            logger.info(f"✅ steam_bd: {var_intSucessoBD} inseridos, {var_intErroBD} erros")
        
        PostgreSQL.desconectar()
        logger.info("🔌 Desconectado do SUPABASE")
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar/importar para o SUPABASE: {e}")
        return
    
    # ========================================
    # PASSO 4: Resumo Final
    # ========================================
    logger.info("")
    logger.info("=" * 70)
    logger.info("🎉 MIGRAÇÃO CONCLUÍDA!")
    logger.info("=" * 70)
    logger.info(f"📊 RESUMO FINAL:")
    logger.info(f"   - steam_raw: {var_intSucessoRaw}/{len(var_listDadosRaw)} migrados")
    logger.info(f"   - steam_bd: {var_intSucessoBD}/{len(var_listDadosBD)} migrados")
    logger.info(f"   - TOTAL: {var_intSucessoRaw + var_intSucessoBD}/{var_intTotalRegistros} registros")
    logger.info("")
    logger.info("✅ Seus dados agora estão na nuvem (Supabase)!")
    logger.info("💡 Você pode verificar em: https://supabase.com/dashboard")
    logger.info("   → Table Editor → steam_raw / steam_bd")
    logger.info("=" * 70)

if __name__ == "__main__":
    from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
    
    # Configurar logging
    Settings.configure_logging()
    
    # Confirmação antes de executar
    print("")
    print("⚠️  ATENÇÃO: Este script irá migrar dados do PostgreSQL LOCAL para o SUPABASE")
    print("")
    print("❓ Você tem PostgreSQL instalado LOCALMENTE no seu computador?")
    print("   (Diferente do Supabase na nuvem)")
    print("")
    
    var_strTemLocal = input("Você tem PostgreSQL local? (sim/não): ").strip().lower()
    
    if var_strTemLocal not in ['sim', 's', 'yes', 'y']:
        print("")
        print("ℹ️  Você NÃO precisa migrar dados!")
        print("")
        print("✅ Seu banco de dados já está na nuvem (Supabase).")
        print("✅ Todos os dados novos serão salvos diretamente no Supabase.")
        print("")
        print("💡 Próximos passos:")
        print("   1. Use a classe PostgreSQL normalmente")
        print("   2. Os dados serão salvos automaticamente no Supabase")
        print("   3. Acesse https://supabase.com/dashboard para ver seus dados")
        print("")
        exit(0)
    
    print("")
    print("📋 Configurações do banco LOCAL:")
    print("")
    
    var_strHost = input("Host (padrão: localhost): ").strip() or "localhost"
    var_strPort = input("Porta (padrão: 5432): ").strip() or "5432"
    var_strUser = input("Usuário (padrão: postgres): ").strip() or "postgres"
    var_strPassword = input("Senha (padrão: postgres): ").strip() or "postgres"
    var_strDatabase = input("Nome do banco (padrão: postgres): ").strip() or "postgres"
    
    print("")
    print("📋 Resumo da configuração:")
    print(f"   - Host: {var_strHost}")
    print(f"   - Porta: {var_strPort}")
    print(f"   - Usuário: {var_strUser}")
    print(f"   - Banco: {var_strDatabase}")
    print("")
    
    var_strResposta = input("Confirmar migração com essas configurações? (sim/não): ").strip().lower()
    
    if var_strResposta in ['sim', 's', 'yes', 'y']:
        # Atualizar as variáveis de ambiente
        os.environ["DB_HOST"] = var_strHost
        os.environ["DB_PORT"] = var_strPort
        os.environ["DB_USER"] = var_strUser
        os.environ["DB_PASSWORD"] = var_strPassword
        os.environ["DB_NAME"] = var_strDatabase
        
        migrar_dados()
    else:
        print("❌ Migração cancelada.")
