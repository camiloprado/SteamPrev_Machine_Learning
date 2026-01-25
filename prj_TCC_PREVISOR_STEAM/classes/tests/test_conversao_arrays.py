"""Script de teste para diagnóstico de conversão de arrays PostgreSQL"""
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Conectar ao PostgreSQL
conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="postgres",
    user="postgres",
    password="Fkmij62uDMmZ3nM1"
)

# Buscar 5 registros com arrays
with conn.cursor(cursor_factory=RealDictCursor) as cursor:
    cursor.execute("""
        SELECT appid, categorias, genero, linguagens 
        FROM steam_unificado 
        WHERE categorias IS NOT NULL 
        LIMIT 5
    """)
    rows = cursor.fetchall()

conn.close()

print("\n" + "="*80)
print("DIAGNÓSTICO: Valores do PostgreSQL")
print("="*80)

for i, row in enumerate(rows):
    print(f"\n[{i}] AppID: {row['appid']}")
    for col in ['categorias', 'genero', 'linguagens']:
        val = row[col]
        print(f"  {col}:")
        print(f"    Tipo Python: {type(val).__name__}")
        print(f"    Valor: {repr(val)}")
        print(f"    É lista?: {isinstance(val, list)}")
        
        if isinstance(val, list):
            print(f"    Tentando join: '{', '.join(val) if val else ''}'")

print("\n" + "="*80)
print("Criando DataFrame e aplicando conversão...")
print("="*80)

df = pd.DataFrame(rows)
print(f"\nDataFrame shape: {df.shape}")
print(f"Tipos: {df.dtypes.to_dict()}")

# Aplicar a função de conversão
def converter_lista(x):
    if not isinstance(x, list):
        return str(x) if pd.notna(x) else ''
    if not x:
        return ''
    try:
        return ', '.join(x)
    except TypeError:
        return str(x)

for col in ['categorias', 'genero', 'linguagens']:
    print(f"\n[{col}] ANTES conversão:")
    print(f"  Tipo: {df[col].dtype}")
    print(f"  Amostra: {list(df[col].head(3))}")
    
    df[col] = df[col].apply(converter_lista)
    
    print(f"[{col}] DEPOIS conversão:")
    print(f"  Tipo: {df[col].dtype}")
    print(f"  Amostra: {list(df[col].head(3))}")
    print(f"  Valores únicos: {df[col].nunique()}")
    print(f"  Primeiros 3 únicos: {list(df[col].unique()[:3])}")

print("\n" + "="*80)
print("DIAGNÓSTICO COMPLETO!")
print("="*80)
