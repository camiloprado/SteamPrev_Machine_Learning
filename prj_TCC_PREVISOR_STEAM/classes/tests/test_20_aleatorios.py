"""
Teste com 100 AppIDs ALEATÓRIOS
Valida normalização e qualidade de dados em amostra representativa
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

def buscar_appids_aleatorios(arg_intQuantidade=100):
    """
    Busca AppIDs aleatórios do banco PostgreSQL
    """
    print("=" * 80)
    print(f"Buscando {arg_intQuantidade} AppIDs aleatórios do PostgreSQL...")
    print("=" * 80)
    
    PostgreSQL.conectar()
    
    # Busca todos os AppIDs e seleciona aleatoriamente
    var_listTodosAppids = PostgreSQL.buscar_todos_appids("steam_raw")
    
    if not var_listTodosAppids:
        print(">>> ERRO: Nenhum AppID encontrado!")
        return []
    
    # Seleciona amostra aleatória
    import random
    var_intQuantidadeReal = min(arg_intQuantidade, len(var_listTodosAppids))
    var_listAppids = random.sample(var_listTodosAppids, var_intQuantidadeReal)
    
    print(f"\n>>> {len(var_listAppids)} AppIDs selecionados aleatoriamente:")
    print(f"    {var_listAppids}")
    print("\n" + "=" * 80)
    
    return var_listAppids

def analisar_qualidade_dados(arg_listAppids):
    """
    Analisa a qualidade dos dados transformados
    """
    print("\n" + "=" * 80)
    print("ANALISE DE QUALIDADE DE DADOS")
    print("=" * 80)
    
    var_dictEstatisticas = {
        "total_processados": 0,
        "total_erros": 0,
        "problemas_acentuacao": [],
        "problemas_corrupcao": [],
        "problemas_data": [],
        "classificacoes": {},
        "campos_vazios": {}
    }
    
    PostgreSQL.conectar()
    
    for var_intAppid in arg_listAppids:
        try:
            print(f"\n[{var_dictEstatisticas['total_processados'] + 1}/{len(arg_listAppids)}] Processando AppID {var_intAppid}...")
            
            # Busca dados RAW
            var_dictDadosRaw = PostgreSQL.buscar_dados(var_intAppid, "steam_raw")
            if not var_dictDadosRaw:
                print(f"    >>> AVISO: AppID {var_intAppid} sem dados")
                var_dictEstatisticas["total_erros"] += 1
                continue
            
            # Transforma dados
            var_dictDadosEstruturados = ProcessadorETL.transformar_raw_para_bd(var_dictDadosRaw)
            
            # Nome do jogo para referência
            var_strNome = var_dictDadosEstruturados.get('nome', 'Desconhecido')
            print(f"    Jogo: {var_strNome}")
            
            # Analisa cada campo
            for var_strCampo, var_anyValor in var_dictDadosEstruturados.items():
                # Verifica acentuação
                if isinstance(var_anyValor, str):
                    if any(c in var_anyValor for c in ['ã', 'á', 'à', 'â', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç', 'Ã', 'Á', 'É', 'Ç']):
                        var_dictEstatisticas["problemas_acentuacao"].append({
                            "appid": var_intAppid,
                            "nome": var_strNome,
                            "campo": var_strCampo,
                            "valor": var_anyValor[:100]
                        })
                elif isinstance(var_anyValor, list):
                    for item in var_anyValor:
                        if isinstance(item, str) and any(c in item for c in ['ã', 'á', 'à', 'â', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç']):
                            var_dictEstatisticas["problemas_acentuacao"].append({
                                "appid": var_intAppid,
                                "nome": var_strNome,
                                "campo": var_strCampo,
                                "valor": item
                            })
                            break
                
                # Verifica corrupção
                if isinstance(var_anyValor, str):
                    if '?' in var_anyValor or '�' in var_anyValor:
                        var_dictEstatisticas["problemas_corrupcao"].append({
                            "appid": var_intAppid,
                            "nome": var_strNome,
                            "campo": var_strCampo,
                            "valor": var_anyValor[:100]
                        })
                
                # Verifica data
                if var_strCampo == 'data_lancamento' and var_anyValor:
                    import re
                    if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(var_anyValor)):
                        var_dictEstatisticas["problemas_data"].append({
                            "appid": var_intAppid,
                            "nome": var_strNome,
                            "valor": var_anyValor
                        })
                
                # Conta classificações
                if var_strCampo == 'classificacao_etaria':
                    var_strClassif = str(var_anyValor)
                    if var_strClassif not in var_dictEstatisticas["classificacoes"]:
                        var_dictEstatisticas["classificacoes"][var_strClassif] = 0
                    var_dictEstatisticas["classificacoes"][var_strClassif] += 1
                
                # Conta campos vazios
                if var_anyValor is None or (isinstance(var_anyValor, str) and var_anyValor.strip() == ""):
                    if var_strCampo not in var_dictEstatisticas["campos_vazios"]:
                        var_dictEstatisticas["campos_vazios"][var_strCampo] = 0
                    var_dictEstatisticas["campos_vazios"][var_strCampo] += 1
            
            var_dictEstatisticas["total_processados"] += 1
            print(f"    >>> OK")
            
        except Exception as e:
            print(f"    >>> ERRO: {e}")
            var_dictEstatisticas["total_erros"] += 1
    
    # Exibe relatório
    print("\n" + "=" * 80)
    print("RELATORIO DE QUALIDADE")
    print("=" * 80)
    
    print(f"\n[RESUMO]")
    print(f"  Total processados: {var_dictEstatisticas['total_processados']}/{len(arg_listAppids)}")
    print(f"  Total com erros: {var_dictEstatisticas['total_erros']}")
    print(f"  Taxa de sucesso: {(var_dictEstatisticas['total_processados']/len(arg_listAppids)*100):.1f}%")
    
    print(f"\n[CLASSIFICACOES ETARIAS]")
    for var_strClassif, var_intQtd in sorted(var_dictEstatisticas["classificacoes"].items()):
        print(f"  {var_strClassif}: {var_intQtd} jogos")
    
    print(f"\n[CAMPOS VAZIOS]")
    if var_dictEstatisticas["campos_vazios"]:
        for var_strCampo, var_intQtd in sorted(var_dictEstatisticas["campos_vazios"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {var_strCampo}: {var_intQtd} jogos ({var_intQtd/var_dictEstatisticas['total_processados']*100:.1f}%)")
    else:
        print("  >>> Nenhum campo vazio encontrado!")
    
    print(f"\n[PROBLEMAS DE ACENTUACAO]")
    if var_dictEstatisticas["problemas_acentuacao"]:
        print(f"  >>> ENCONTRADOS {len(var_dictEstatisticas['problemas_acentuacao'])} PROBLEMAS!")
        for var_dictProblema in var_dictEstatisticas["problemas_acentuacao"][:5]:
            print(f"      AppID {var_dictProblema['appid']} ({var_dictProblema['nome']})")
            print(f"      Campo: {var_dictProblema['campo']}")
            print(f"      Valor: {var_dictProblema['valor']}")
    else:
        print("  >>> Nenhum problema de acentuacao encontrado!")
    
    print(f"\n[PROBLEMAS DE CORRUPCAO]")
    if var_dictEstatisticas["problemas_corrupcao"]:
        print(f"  >>> ENCONTRADOS {len(var_dictEstatisticas['problemas_corrupcao'])} PROBLEMAS!")
        for var_dictProblema in var_dictEstatisticas["problemas_corrupcao"][:5]:
            print(f"      AppID {var_dictProblema['appid']} ({var_dictProblema['nome']})")
            print(f"      Campo: {var_dictProblema['campo']}")
            print(f"      Valor: {var_dictProblema['valor']}")
    else:
        print("  >>> Nenhum problema de corrupcao encontrado!")
    
    print(f"\n[PROBLEMAS DE DATA]")
    if var_dictEstatisticas["problemas_data"]:
        print(f"  >>> ENCONTRADOS {len(var_dictEstatisticas['problemas_data'])} PROBLEMAS!")
        for var_dictProblema in var_dictEstatisticas["problemas_data"][:5]:
            print(f"      AppID {var_dictProblema['appid']} ({var_dictProblema['nome']})")
            print(f"      Valor: {var_dictProblema['valor']}")
    else:
        print("  >>> Nenhum problema de data encontrado!")
    
    print("\n" + "=" * 80)
    
    return var_dictEstatisticas

def inserir_lote_supabase(arg_listAppids):
    """
    Insere um lote de AppIDs no Supabase
    """
    print("\n" + "=" * 80)
    print("INSERINDO LOTE NO SUPABASE")
    print("=" * 80)
    
    try:
        ProcessadorETL.processar_lote(arg_listAppids)
        print("\n>>> LOTE PROCESSADO COM SUCESSO!")
        
        # Verifica inserção
        SupabaseDB.conectar()
        var_intContador = 0
        for var_intAppid in arg_listAppids[:5]:  # Verifica os primeiros 5
            var_dictDados = SupabaseDB.buscar_dadosSteamBD(var_intAppid)
            if var_dictDados:
                var_intContador += 1
                print(f"  >>> AppID {var_intAppid}: OK")
        
        print(f"\n>>> {var_intContador}/5 verificados e confirmados no Supabase!")
        
    except Exception as e:
        print(f"\n>>> ERRO ao processar lote: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        print("\n>>> TESTE COM 100 APPIDS ALEATORIOS\n")
        
        # Passo 1: Buscar AppIDs aleatórios
        var_listAppids = buscar_appids_aleatorios(100)
        
        if not var_listAppids:
            print(">>> ERRO: Nenhum AppID para processar!")
            sys.exit(1)
        
        # Passo 2: Analisar qualidade dos dados
        var_dictEstatisticas = analisar_qualidade_dados(var_listAppids)
        
        # Passo 3: Inserir no Supabase
        print("\n" + "=" * 80)
        var_strResposta = input("Deseja inserir estes jogos no Supabase? (s/n): ")
        if var_strResposta.lower() == 's':
            inserir_lote_supabase(var_listAppids)
        else:
            print(">>> Insercao no Supabase cancelada pelo usuario")
        
        print("\n" + "=" * 80)
        print(">>> TESTE CONCLUIDO!")
        print("=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n>>> Teste interrompido pelo usuario")
    except Exception as e:
        print(f"\n>>> ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        PostgreSQL.desconectar()
