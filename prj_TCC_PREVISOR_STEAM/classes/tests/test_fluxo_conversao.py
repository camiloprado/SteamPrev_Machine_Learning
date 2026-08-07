"""Teste rápido do fluxo de conversão + processamento categórico"""
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, r"D:\Projeto_TCC_CC")

from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorLimpeza import ProcessadorLimpeza

print("\n" + "="*80)
print("TESTE DE FLUXO: Conversão + Processamento Categórico")
print("="*80)

# Conectar e buscar amostra
conn = psycopg2.connect(
    host="127.0.0.1", port=5432, database="postgres",
    user="postgres", password=os.getenv("DB_PASSWORD", "postgres")
)

with conn.cursor(cursor_factory=RealDictCursor) as cursor:
    cursor.execute("""
        SELECT appid, categorias, genero, linguagens, desenvolvedores, distribuidores
        FROM steam_unificado 
        WHERE categorias IS NOT NULL 
        LIMIT 1000
    """)
    rows = cursor.fetchall()
conn.close()

df = pd.DataFrame(rows)
print(f"\n✓ DataFrame carregado: {df.shape}")
print(f"  Tipos ANTES: {df.dtypes.to_dict()}")
print(f"\n  Amostra categorias (primeiros 3):")
for i, val in enumerate(df['categorias'].head(3)):
    print(f"    [{i}] tipo={type(val).__name__}: {repr(val)}")

# ETAPA 1: Conversão (simulando linha 1062)
print("\n" + "-"*80)
print("ETAPA 1: Convertendo arrays PostgreSQL...")
print("-"*80)
df_convertido = ProcessadorLimpeza.limpar_valores_nao_hashable(df, arg_boolInplace=False)

print(f"\n✓ Conversão concluída!")
print(f"  Tipos DEPOIS: {df_convertido.dtypes.to_dict()}")
print(f"\n  Amostra categorias convertidas (primeiros 3):")
for i, val in enumerate(df_convertido['categorias'].head(3)):
    print(f"    [{i}] tipo={type(val).__name__}: {repr(val)}")

print(f"\n  Valores únicos em 'categorias': {df_convertido['categorias'].nunique()}")
print(f"  Valores únicos em 'genero': {df_convertido['genero'].nunique()}")

# ETAPA 2: Processamento Categórico (simulando processar_categoricos)
print("\n" + "-"*80)
print("ETAPA 2: Processando categóricos...")
print("-"*80)

# Simular apenas a parte relevante
from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorLimpeza import MultiLabelBinarizerTransformer

for col in ['categorias', 'genero']:
    print(f"\n[{col}] Processando:")
    print(f"  Amostra: {list(df_convertido[col].head(3))}")
    
    transformer = MultiLabelBinarizerTransformer(arg_intMaxFeatures=50, arg_intMinFreq=10)
    transformer.fit(df_convertido[[col]])
    
    print(f"  Categorias encontradas: {len(transformer.var_listCategories_)}")
    if len(transformer.var_listCategories_) > 0:
        print(f"  Top 5: {transformer.var_listCategories_[:5]}")

print("\n" + "="*80)
print("TESTE COMPLETO!")
print("="*80)
