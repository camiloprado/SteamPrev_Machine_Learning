"""
Script para exportar todas as tabelas do Docker PostgreSQL para CSV.
Gera arquivos CSV de: steam_raw, steam_bd, steam_generico, steam_unificado, itad_raw, steam_itad_mapping
"""

import sys
import os
import csv
import json
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
import logging

Settings.configure_logging()
logger = logging.getLogger(__name__)

def exportar_tabela_csv(
    arg_strNomeTabela: str,
    arg_strArquivoSaida: str = None,
    arg_intBatchSize: int = 1000,
    arg_intLimit: int = None
):
    """
    Exporta uma tabela do PostgreSQL para CSV.
    
    Parâmetros:
    - arg_strNomeTabela (str): Nome da tabela no banco
    - arg_strArquivoSaida (str): Caminho do arquivo de saída (None = auto)
    - arg_intBatchSize (int): Tamanho do batch para leitura
    - arg_intLimit (int): Limite de registros (None = todos)
    """
    try:
        # Define arquivo de saída
        if not arg_strArquivoSaida:
            var_strDiretorio = os.path.join("prj_TCC_PREVISOR_STEAM", "resources", "dados", "exports")
            os.makedirs(var_strDiretorio, exist_ok=True)
            var_strTimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arg_strArquivoSaida = os.path.join(var_strDiretorio, f"{arg_strNomeTabela}_{var_strTimestamp}.csv")
        
        logger.info(f"Exportando {arg_strNomeTabela} para CSV...")
        logger.info(f"   Arquivo: {arg_strArquivoSaida}")
        
        # Conecta ao banco
        PostgreSQL.conectar()
        
        # Conta total de registros
        var_strSQLCount = f"SELECT COUNT(*) FROM {arg_strNomeTabela}"
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQLCount)
            var_intTotal = cursor.fetchone()[0]
        
        if arg_intLimit:
            var_intTotal = min(var_intTotal, arg_intLimit)
        
        logger.info(f"   Total de registros: {var_intTotal:,}")
        
        # Busca colunas da tabela
        var_strSQLColunas = f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{arg_strNomeTabela}' 
        ORDER BY ordinal_position;
        """
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQLColunas)
            var_listColunas = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"   Colunas: {len(var_listColunas)}")
        
        # Abre arquivo CSV
        var_intProcessados = 0
        with open(arg_strArquivoSaida, 'w', newline='', encoding='utf-8') as csvfile:
            var_csvWriter = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            
            # Escreve cabeçalho
            var_csvWriter.writerow(var_listColunas)
            
            # Descobre a chave primária da tabela
            var_strSQLPK = f"""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = '{arg_strNomeTabela}'::regclass AND i.indisprimary;
            """
            
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLPK)
                var_tupPK = cursor.fetchone()
                var_strColunaOrdem = var_tupPK[0] if var_tupPK else var_listColunas[0]
            
            logger.info(f"   Usando coluna '{var_strColunaOrdem}' para paginação (keyset)")
            
            # Processa em batches usando KEYSET PAGINATION (mantém performance constante)
            var_objUltimoCursor = None  # Valor do último registro processado
            
            while var_intProcessados < var_intTotal:
                # Busca batch usando WHERE > last_key (keyset pagination)
                if var_objUltimoCursor is None:
                    var_strSQLBatch = f"""
                    SELECT * FROM {arg_strNomeTabela}
                    ORDER BY {var_strColunaOrdem}
                    LIMIT {arg_intBatchSize};
                    """
                else:
                    # Escapa valor para evitar SQL injection
                    if isinstance(var_objUltimoCursor, str):
                        var_strCursorEscapado = var_objUltimoCursor.replace("'", "''")
                        var_strCondicao = f"{var_strColunaOrdem} > '{var_strCursorEscapado}'"
                    else:
                        var_strCondicao = f"{var_strColunaOrdem} > {var_objUltimoCursor}"
                    
                    var_strSQLBatch = f"""
                    SELECT * FROM {arg_strNomeTabela}
                    WHERE {var_strCondicao}
                    ORDER BY {var_strColunaOrdem}
                    LIMIT {arg_intBatchSize};
                    """
                
                with PostgreSQL._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQLBatch)
                    var_listRegistros = cursor.fetchall()
                
                if not var_listRegistros:
                    logger.info(f"   Nenhum registro encontrado após cursor {var_objUltimoCursor}. Finalizando.")
                    break
                
                # Escreve linhas (converte JSONB para string)
                for var_tupleRegistro in var_listRegistros:
                    var_listLinha = []
                    for var_objValor in var_tupleRegistro:
                        # Converte JSONB/dicts para JSON string
                        if isinstance(var_objValor, dict):
                            var_listLinha.append(json.dumps(var_objValor, ensure_ascii=False))
                        # Converte listas para string PostgreSQL array
                        elif isinstance(var_objValor, list):
                            var_listLinha.append('{' + ','.join(map(str, var_objValor)) + '}')
                        # Converte None para string vazia
                        elif var_objValor is None:
                            var_listLinha.append('')
                        else:
                            var_listLinha.append(str(var_objValor))
                    
                    var_csvWriter.writerow(var_listLinha)
                    
                    # Atualiza cursor para próximo batch (último valor da coluna de ordem)
                    var_intIndiceColunaOrdem = var_listColunas.index(var_strColunaOrdem)
                    var_objUltimoCursor = var_tupleRegistro[var_intIndiceColunaOrdem]
                
                var_intProcessados += len(var_listRegistros)
                
                # Log de progresso
                var_fltProgresso = (var_intProcessados / var_intTotal) * 100
                logger.info(f"   Progresso: {var_intProcessados:,}/{var_intTotal:,} ({var_fltProgresso:.1f}%)")
                
                if len(var_listRegistros) < arg_intBatchSize:
                    break
        
        # Estatísticas finais
        var_intTamanhoMB = os.path.getsize(arg_strArquivoSaida) / (1024 * 1024)
        logger.info(f"Exportação concluída!")
        logger.info(f"   Arquivo: {arg_strArquivoSaida}")
        logger.info(f"   Tamanho: {var_intTamanhoMB:.2f} MB")
        logger.info(f"   Registros: {var_intProcessados:,}")
        
        return arg_strArquivoSaida
        
    except Exception as e:
        logger.error(f"Erro ao exportar {arg_strNomeTabela}: {e}")
        raise
    finally:
        PostgreSQL.desconectar()


def exportar_todas_tabelas(arg_strDiretorioSaida: str = None):
    """
    Exporta todas as tabelas principais do Docker para CSV.
    """
    var_listTabelas = [
        "steam_generico",
        "steam_raw",
        "steam_generico",
        "steam_unificado",
        "itad_raw",
        "steam_itad_mapping"
    ]
    
    logger.info("=" * 70)
    logger.info("EXPORTAÇÃO COMPLETA: Todas as Tabelas → CSV")
    logger.info("=" * 70)
    
    var_dictResultados = {}
    
    for var_strTabela in var_listTabelas:
        try:
            logger.info(f"\nTabela: {var_strTabela}")
            logger.info("-" * 70)
            
            var_strArquivo = exportar_tabela_csv(
                arg_strNomeTabela=var_strTabela,
                arg_strArquivoSaida=arg_strDiretorioSaida
            )
            
            var_dictResultados[var_strTabela] = {
                "arquivo": var_strArquivo,
                "sucesso": True
            }
            
        except Exception as e:
            logger.error(f"Falha em {var_strTabela}: {e}")
            var_dictResultados[var_strTabela] = {
                "arquivo": None,
                "sucesso": False,
                "erro": str(e)
            }
    
    # Resumo final
    logger.info("\n" + "=" * 70)
    logger.info("RESUMO DA EXPORTAÇÃO")
    logger.info("=" * 70)
    
    var_intSucesso = sum(1 for v in var_dictResultados.values() if v["sucesso"])
    var_intTotal = len(var_dictResultados)
    
    for var_strTabela, var_dictInfo in var_dictResultados.items():
        if var_dictInfo["sucesso"]:
            logger.info(f"{var_strTabela:<25} → {var_dictInfo['arquivo']}")
        else:
            logger.info(f"{var_strTabela:<25} → ERRO: {var_dictInfo.get('erro', 'Desconhecido')}")
    
    logger.info("=" * 70)
    logger.info(f"Total: {var_intSucesso}/{var_intTotal} tabelas exportadas com sucesso")
    logger.info("=" * 70)
    
    return var_dictResultados


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Exporta tabelas do Docker PostgreSQL para CSV")
    parser.add_argument(
        '--tabela',
        type=str,
        help='Nome da tabela específica (deixe vazio para exportar todas)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Arquivo de saída (apenas para tabela específica)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Tamanho do batch (padrão: 1000)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limite de registros (None = todos)'
    )
    
    args = parser.parse_args()
    
    if args.tabela:
        # Exporta tabela específica
        print(f"\nExportando tabela: {args.tabela}\n")
        exportar_tabela_csv(
            arg_strNomeTabela=args.tabela,
            arg_strArquivoSaida=args.output,
            arg_intBatchSize=args.batch_size,
            arg_intLimit=args.limit
        )
    else:
        # Exporta todas as tabelas
        print("\nExportando TODAS as tabelas...\n")
        exportar_todas_tabelas()