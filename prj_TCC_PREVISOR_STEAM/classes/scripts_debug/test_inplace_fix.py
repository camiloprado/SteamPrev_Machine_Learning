"""Teste local de conversão inplace vs copy"""
import pandas as pd

# Simular dados com listas
data = {
    'categorias': [['Um jogador', 'Multi'], ['Acao'], ['RPG', 'Indie']],
    'genero': [['Acao'], ['RPG'], ['Indie', 'Casual']],
    'valor': [10.5, 20.0, 30.5]
}
df_original = pd.DataFrame(data)

print("="*80)
print("TESTE 1: SEM CAPTURAR RETORNO (como estava antes)")
print("="*80)

df_test1 = df_original.copy()
print("\nANTES:")
print(df_test1['categorias'].head())
print(f"Tipos: {[type(x).__name__ for x in df_test1['categorias']]}")

# Simular o que estava acontecendo
df_work = df_test1  # Não usa copy
df_work['categorias'] = df_work['categorias'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
# NÃO captura o retorno

print("\nDEPOIS (sem capturar df_work):")
print(df_test1['categorias'].head())
print(f"Tipos: {[type(x).__name__ for x in df_test1['categorias']]}")
print(f"df_test1 foi modificado?: {df_test1['categorias'].iloc[0] == 'Um jogador, Multi'}")

print("\n" + "="*80)
print("TESTE 2: CAPTURANDO RETORNO (fix aplicado)")
print("="*80)

def limpar_inplace(df, inplace=False):
    df_work = df if inplace else df.copy()
    df_work['categorias'] = df_work['categorias'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
    return df_work

df_test2 = df_original.copy()
print("\nANTES:")
print(df_test2['categorias'].head())

# SEM capturar (problema!)
limpar_inplace(df_test2, inplace=True)
print("\nDEPOIS (inplace=True SEM capturar):")
print(df_test2['categorias'].head())
print(f"Modificado?: {df_test2['categorias'].iloc[0] == 'Um jogador, Multi'}")

# COM captura (solução!)
df_test3 = df_original.copy()
df_test3 = limpar_inplace(df_test3, inplace=True)
print("\nDEPOIS (inplace=True COM capturar):")
print(df_test3['categorias'].head())
print(f"Modificado?: {df_test3['categorias'].iloc[0] == 'Um jogador, Multi'}")

print("\n" + "="*80)
print("CONCLUSÃO:")
print("="*80)
print("Mesmo com inplace=True, SE a função modifica via assignment (df['col'] = ...),")
print("a modificação PERSISTE porque df_work É o mesmo objeto que o argumento.")
print("O problema era que a CHAMADA não estava capturando o retorno!")
