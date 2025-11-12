"""
Teste com dados REAIS dos AppIDs 10 e 1620
- AppID 10: Counter-Strike (classificação L)
- AppID 1620: Harmony (classificação 18)
Valida todo o pipeline de processamento ETL
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

def test_buscar_dados_raw(arg_intAppid):
    """
    Busca dados brutos de um AppID no PostgreSQL
    """
    print("=" * 80)
    print(f"TESTE: Buscar Dados RAW do AppID {arg_intAppid}")
    print("=" * 80)
    
    PostgreSQL.conectar()
    
    print(f"\n[1] Buscando dados brutos no PostgreSQL (Docker)...")
    var_dictDadosRaw = PostgreSQL.buscar_dados(arg_intAppid, "steam_raw")
    
    if not var_dictDadosRaw:
        print(f">>> ERRO: AppID {arg_intAppid} não encontrado no banco!")
        return None
    
    print(f">>> Dados encontrados!")
    print(f"\n[ESTRUTURA] Estrutura dos dados:")
    print(f"  - AppID: {var_dictDadosRaw.get('appid')}")
    print(f"  - Tem detalhes: {'Sim' if var_dictDadosRaw.get('detalhes') else 'Não'}")
    print(f"  - Tem reviews: {'Sim' if var_dictDadosRaw.get('reviews') else 'Não'}")
    
    if var_dictDadosRaw.get('detalhes'):
        var_dictDetalhes = var_dictDadosRaw['detalhes']
        print(f"\n[INFO] Informações do Jogo:")
        print(f"  - Nome: {var_dictDetalhes.get('name', 'N/A')}")
        print(f"  - Classificação Etária RAW: {var_dictDetalhes.get('required_age', 'N/A')}")
        print(f"  - Gêneros RAW: {[g.get('description') for g in var_dictDetalhes.get('genres', [])]}")
        print(f"  - Data RAW: {var_dictDetalhes.get('release_date', {}).get('date', 'N/A')}")
        print(f"  - Linguagens RAW: {var_dictDetalhes.get('supported_languages', 'N/A')[:100]}...")
        print(f"  - Desenvolvedores: {var_dictDetalhes.get('developers', [])}")
        print(f"  - Preço RAW: {var_dictDetalhes.get('price_overview')}")
        
        print(f"\n[RAW] TODOS OS CAMPOS DETALHES (RAW):")
        import json
        print(json.dumps(var_dictDetalhes, indent=2, ensure_ascii=False)[:2000] + "\n... (truncado)")
    
    if var_dictDadosRaw.get('reviews'):
        var_dictReviews = var_dictDadosRaw['reviews']
        print(f"\n[REVIEWS] Reviews:")
        print(f"  - Review Score: {var_dictReviews.get('review_score', 'N/A')}")
        print(f"  - Total Reviews: {var_dictReviews.get('total_reviews', 0):,}")
        print(f"  - Positivos: {var_dictReviews.get('total_positive', 0):,}")
        print(f"  - Negativos: {var_dictReviews.get('total_negative', 0):,}")
        print(f"  - Descrição: {var_dictReviews.get('review_score_desc', 'N/A')}")
        
        print(f"\n[RAW] TODOS OS CAMPOS REVIEWS (RAW):")
        import json
        print(json.dumps(var_dictReviews, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    return var_dictDadosRaw

def test_transformar_dados(arg_dictDadosRaw):
    """
    Transforma dados brutos em dados estruturados
    """
    print("\n" + "=" * 80)
    print("TESTE: Transformar Dados RAW para Estruturados")
    print("=" * 80)
    
    if not arg_dictDadosRaw:
        print(">>> ERRO: Sem dados para transformar!")
        return None
    
    print("\n[2] Aplicando transformações ETL...")
    
    try:
        var_dictDadosEstruturados = ProcessadorETL.transformar_raw_para_bd(arg_dictDadosRaw)
        
        print(">>> Transformação concluída com sucesso!")
        
        print(f"\n[DADOS] TODOS OS CAMPOS ESTRUTURADOS:")
        import json
        for var_strCampo, var_anyValor in var_dictDadosEstruturados.items():
            print(f"  - {var_strCampo}: {var_anyValor}")
        
        print(f"\n[ANALISE] Verificações Detalhadas:")
        
        # Verifica cada campo individualmente
        for var_strCampo, var_anyValor in var_dictDadosEstruturados.items():
            var_strTipo = type(var_anyValor).__name__
            var_strRepr = str(var_anyValor)[:100]
            
            # Análise de problemas potenciais
            var_listProblemas = []
            
            # Verifica strings vazias ou None
            if var_anyValor is None:
                var_listProblemas.append("NULL")
            elif isinstance(var_anyValor, str) and var_anyValor.strip() == "":
                var_listProblemas.append("VAZIO")
            elif isinstance(var_anyValor, list) and len(var_anyValor) == 0:
                var_listProblemas.append("LISTA VAZIA")
            
            # Verifica acentuação (se for string ou lista de strings)
            if isinstance(var_anyValor, str):
                if any(c in var_anyValor for c in ['ã', 'á', 'à', 'â', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç']):
                    var_listProblemas.append("AVISO: TEM ACENTUACAO")
            elif isinstance(var_anyValor, list):
                for item in var_anyValor:
                    if isinstance(item, str) and any(c in item for c in ['ã', 'á', 'à', 'â', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç']):
                        var_listProblemas.append(f"AVISO: TEM ACENTUACAO EM: {item}")
                        break
            
            # Verifica caracteres corrompidos
            if isinstance(var_anyValor, str):
                if '?' in var_anyValor or '�' in var_anyValor:
                    var_listProblemas.append("AVISO: CARACTERES CORROMPIDOS")
            elif isinstance(var_anyValor, list):
                for item in var_anyValor:
                    if isinstance(item, str) and ('?' in item or '�' in item):
                        var_listProblemas.append(f"AVISO: CORROMPIDO EM: {item}")
                        break
            
            # Verifica formato de data
            if var_strCampo == 'data_lancamento' and var_anyValor:
                import re
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(var_anyValor)):
                    var_listProblemas.append("AVISO: FORMATO DATA INVALIDO")
            
            # Exibe status
            var_strStatus = " | ".join(var_listProblemas) if var_listProblemas else "OK"
            print(f"    [{var_strTipo:>10}] {var_strCampo:25} = {var_strRepr:50} | {var_strStatus}")
        
        print(f"\n[VALIDACAO] Verificações Gerais:")
        
        # Verifica classificação etária
        var_strClassificacao = var_dictDadosEstruturados.get('classificacao_etaria', '')
        if var_strClassificacao in ['L', '10', '12', '14', '16', '18']:
            print(f"  >>> OK: Classificação etária formatada: {var_strClassificacao}")
        else:
            print(f"  >>> AVISO: Classificação etária não reconhecida: {var_strClassificacao}")
        
        # Verifica gêneros
        var_listGeneros = var_dictDadosEstruturados.get('genero', [])
        if var_listGeneros:
            var_boolTemAcentuacao = any('ç' in g or 'ã' in g or 'á' in g or 'é' in g for g in var_listGeneros)
            if not var_boolTemAcentuacao:
                print(f"  >>> OK: Gêneros sem acentuação: {var_listGeneros}")
            else:
                print(f"  >>> AVISO: Ainda há acentuação nos gêneros: {var_listGeneros}")
        
        # Verifica data
        var_strData = var_dictDadosEstruturados.get('data_lancamento', '')
        if var_strData:
            import re
            if re.match(r'^\d{4}-\d{2}-\d{2}$', var_strData):
                print(f"  >>> OK: Data no formato ISO: {var_strData}")
            else:
                print(f"  >>> AVISO: Data não está no formato ISO: {var_strData}")
        
        # Verifica linguagens
        var_listLinguagens = var_dictDadosEstruturados.get('linguagens', [])
        if var_listLinguagens:
            var_boolTemCaracteresCorretos = all('?' not in l and '�' not in l for l in var_listLinguagens)
            if var_boolTemCaracteresCorretos:
                print(f"  >>> OK: Linguagens sem caracteres corrompidos")
                print(f"     Primeiras 5: {var_listLinguagens[:5]}")
            else:
                print(f"  >>> AVISO: Ainda há caracteres corrompidos nas linguagens")
        
        print("\n" + "=" * 80)
        return var_dictDadosEstruturados
        
    except Exception as e:
        print(f">>> ERRO na transformação: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_inserir_supabase(arg_dictDadosEstruturados, arg_intAppid):
    """
    Insere dados estruturados no Supabase
    """
    print("\n" + "=" * 80)
    print("TESTE: Inserir no Supabase Cloud")
    print("=" * 80)
    
    if not arg_dictDadosEstruturados:
        print(">>> ERRO: Sem dados para inserir!")
        return False
    
    print("\n[3] Inserindo no Supabase...")
    
    try:
        SupabaseDB.conectar()
        SupabaseDB.inserir_dadosSteamBD([arg_dictDadosEstruturados])
        print(">>> Dados inseridos com sucesso no Supabase!")
        
        print("\n[4] Verificando inserção...")
        var_dictDadosSupabase = SupabaseDB.buscar_dadosSteamBD(arg_intAppid)
        
        if var_dictDadosSupabase:
            print(">>> Dados encontrados no Supabase!")
            print(f"\n[SUPABASE] Dados recuperados:")
            print(f"  - AppID: {var_dictDadosSupabase.get('appid')}")
            print(f"  - Nome: {var_dictDadosSupabase.get('nome')}")
            print(f"  - Classificação Etária: {var_dictDadosSupabase.get('classificacao_etaria')}")
            print(f"  - Gêneros: {var_dictDadosSupabase.get('genero')}")
            print(f"  - Data: {var_dictDadosSupabase.get('data_lancamento')}")
            print(f"  - Última Atualização: {var_dictDadosSupabase.get('ultima_atualizacao')}")
        else:
            print(">>> AVISO: Dados não encontrados após inserção")
        
        print("\n" + "=" * 80)
        return True
        
    except Exception as e:
        print(f">>> ERRO ao inserir no Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pipeline_completo(arg_listAppids):
    """
    Testa o pipeline completo de ETL
    """
    print("\n" + "=" * 80)
    print(f"TESTE COMPLETO: Pipeline ETL com AppIDs {arg_listAppids}")
    print("=" * 80)
    
    print("\n[PIPELINE] Executando pipeline completo:")
    print("  1. Buscar dados RAW (PostgreSQL Docker)")
    print("  2. Transformar dados (ETL)")
    print("  3. Inserir dados (Supabase Cloud)")
    
    try:
        ProcessadorETL.processar_lote(arg_listAppids)
        print("\n>>> PIPELINE COMPLETO EXECUTADO COM SUCESSO!")
        
    except Exception as e:
        print(f"\n>>> ERRO no pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        print("\n>>> TESTE COM DADOS REAIS - AppIDs 10 e 1620\n")
        
        var_listAppids = [10, 1620]
        
        for var_intAppid in var_listAppids:
            print("\n" + "=" * 40)
            print(f"Processando AppID {var_intAppid}")
            print("=" * 40)
            
            # Teste 1: Buscar dados
            var_dictDadosRaw = test_buscar_dados_raw(var_intAppid)
            
            # Teste 2: Transformar dados
            var_dictDadosEstruturados = test_transformar_dados(var_dictDadosRaw)
            
            # Teste 3: Inserir no Supabase
            test_inserir_supabase(var_dictDadosEstruturados, var_intAppid)
        
        # Teste 4: Pipeline completo (alternativa)
        # test_pipeline_completo([10, 1620])
        
        print("\n" + "=" * 80)
        print(">>> TODOS OS TESTES CONCLUIDOS!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n>>> ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        PostgreSQL.desconectar()
