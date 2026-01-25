"""
Script de teste rápido para verificar conversão de arrays PostgreSQL
"""
import pandas as pd
import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Conectar ao banco
conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="postgres",
    user="postgres",
    password="Fkmij62uDMmZ3nM1"
)

cursor = conn.cursor()

# Buscar 10 amostras de cada coluna multi-label
colunas = ['categorias', 'genero', 'linguagens', 'desenvolvedores', 'distribuidores']

for coluna in colunas:
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTANDO: {coluna}")
    logger.info(f"{'='*60}")
    
    # Buscar 5 amostras não-vazias
    cursor.execute(f"""
        SELECT {coluna}
        FROM steam_unificado
        WHERE {coluna} IS NOT NULL 
          AND {coluna} != '{{}}'
        LIMIT 5
    """)
    
    resultados = cursor.fetchall()
    
    logger.info(f"\n  Valores originais do PostgreSQL:")
    for idx, (valor,) in enumerate(resultados, 1):
        logger.info(f"    [{idx}] Tipo Python: {type(valor).__name__}")
        logger.info(f"        Valor: {valor}")
        
        # Simular conversão
        if isinstance(valor, list) and valor:
            convertido = ', '.join(valor)
            logger.info(f"        Convertido: '{convertido}'")
        elif isinstance(valor, list):
            logger.info(f"        Convertido: '' (lista vazia)")
        else:
            logger.info(f"        ⚠ NÃO É LISTA! Tipo: {type(valor)}")

cursor.close()
conn.close()

logger.info(f"\n{'='*60}")
logger.info("TESTE CONCLUÍDO")
logger.info(f"{'='*60}")
