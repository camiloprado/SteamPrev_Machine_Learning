"""
Script de diagnóstico para investigar colunas multi-label vazias.
Execute este script para entender por que as colunas estão retornando total_unique=1
"""

import sys
sys.path.append('D:\\Projeto_TCC_CC')

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnosticar_coluna_multilabel(arg_strNomeTabela: str, arg_strNomeColuna: str):
    """
    Diagnóstica uma coluna multi-label específica
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"DIAGNÓSTICO: {arg_strNomeTabela}.{arg_strNomeColuna}")
    logger.info(f"{'='*60}")
    
    try:
        # Conectar ao banco
        PostgreSQL.conectar()
        
        # Consulta para analisar a coluna
        var_strSQL = f"""
            SELECT 
                {arg_strNomeColuna},
                COUNT(*) as quantidade
            FROM {arg_strNomeTabela}
            GROUP BY {arg_strNomeColuna}
            ORDER BY quantidade DESC
            LIMIT 20;
        """
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL)
            var_listResultados = cursor.fetchall()
            
            logger.info(f"\nTop 20 valores mais comuns:")
            logger.info(f"{'Valor':<50} | {'Quantidade':>10}")
            logger.info(f"{'-'*63}")
            
            for valor, quantidade in var_listResultados:
                var_strValor = str(valor)[:47] + "..." if len(str(valor)) > 50 else str(valor)
                logger.info(f"{var_strValor:<50} | {quantidade:>10,}")
        
        # Estatísticas gerais
        var_strSQLStats = f"""
            SELECT 
                COUNT(*) as total_registros,
                COUNT({arg_strNomeColuna}) as nao_nulos,
                COUNT(DISTINCT {arg_strNomeColuna}) as valores_unicos,
                SUM(CASE WHEN {arg_strNomeColuna} = '' THEN 1 ELSE 0 END) as vazios,
                SUM(CASE WHEN {arg_strNomeColuna} IS NULL THEN 1 ELSE 0 END) as nulos
            FROM {arg_strNomeTabela};
        """
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQLStats)
            stats = cursor.fetchone()
            
            logger.info(f"\nEstatísticas Gerais:")
            logger.info(f"  Total de registros: {stats[0]:,}")
            logger.info(f"  Não-nulos: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
            logger.info(f"  Valores únicos: {stats[2]:,}")
            logger.info(f"  Vazios: {stats[3]:,}")
            logger.info(f"  Nulos: {stats[4]:,}")
            
            if stats[2] == 1:
                logger.warning(f"\n⚠️ PROBLEMA: Apenas 1 valor único encontrado!")
                logger.warning(f"Isso indica que todos os registros têm o mesmo valor.")
        
        # Amostras de valores
        var_strSQLSample = f"""
            SELECT {arg_strNomeColuna}
            FROM {arg_strNomeTabela}
            WHERE {arg_strNomeColuna} IS NOT NULL 
            AND {arg_strNomeColuna} != ''
            LIMIT 5;
        """
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQLSample)
            var_listAmostras = cursor.fetchall()
            
            logger.info(f"\nAmostras de valores:")
            for i, (valor,) in enumerate(var_listAmostras, 1):
                logger.info(f"  {i}. {repr(valor)[:100]}")
                logger.info(f"     Tipo: {type(valor).__name__}, Comprimento: {len(str(valor))}")
                
                # Verificar se é lista ou string separada por vírgula
                var_strValor = str(valor)
                if ',' in var_strValor:
                    var_listItens = [item.strip() for item in var_strValor.split(',')]
                    logger.info(f"     Contém {len(var_listItens)} itens separados por vírgula")
                    logger.info(f"     Primeiros itens: {var_listItens[:3]}")
        
    except Exception as e:
        logger.error(f"Erro ao diagnosticar coluna: {e}", exc_info=True)
    finally:
        PostgreSQL.desconectar()


def main():
    """
    Executa diagnóstico em todas as colunas multi-label
    """
    var_listColunas = [
        ("steam_unificado", "categorias"),
        ("steam_unificado", "genero"),
        ("steam_unificado", "linguagens"),
        ("steam_unificado", "desenvolvedores"),
        ("steam_unificado", "distribuidores"),
    ]
    
    for tabela, coluna in var_listColunas:
        diagnosticar_coluna_multilabel(tabela, coluna)
        print("\n")
    
    logger.info("\n" + "="*60)
    logger.info("DIAGNÓSTICO COMPLETO")
    logger.info("="*60)


if __name__ == "__main__":
    main()
