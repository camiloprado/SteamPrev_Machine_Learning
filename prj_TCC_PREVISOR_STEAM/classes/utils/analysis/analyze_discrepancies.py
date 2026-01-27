"""
Script para analisar discrepâncias entre as tabelas steam_raw, steam_generico e itad
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'prj_TCC_PREVISOR_STEAM'))

from prj_TCC_PREVISOR_STEAM.classes.core.application import InitApplication

# Inicializar conexão
init_app = InitApplication()
db = init_app.get_postgre()
db.conectar()

conn = db._var_connConnection
cursor = conn.cursor()

print("="*80)
print("ANÁLISE DE DISCREPÂNCIAS ENTRE TABELAS")
print("="*80)

# 1. Verificar AppIDs em steam_raw mas não em steam_generico
cursor.execute("""
    SELECT COUNT(*) 
    FROM steam_raw sr 
    WHERE NOT EXISTS (
        SELECT 1 FROM steam_generico sg WHERE sg.appid = sr.appid
    )
""")
raw_sem_generico = cursor.fetchone()[0]
print(f'\n[1] AppIDs em steam_raw mas NAO em steam_generico: {raw_sem_generico:,}')

# 2. Verificar alguns exemplos
cursor.execute("""
    SELECT appid 
    FROM steam_raw sr 
    WHERE NOT EXISTS (
        SELECT 1 FROM steam_generico sg WHERE sg.appid = sr.appid
    )
    ORDER BY appid
    LIMIT 15
""")
exemplos_raw = cursor.fetchall()
print(f'\nExemplos de AppIDs faltando no steam_generico:')
for (appid,) in exemplos_raw:
    print(f'  - AppID: {appid}')

# 3. Verificar AppIDs em steam_generico mas não em steam_raw
cursor.execute("""
    SELECT COUNT(*) 
    FROM steam_generico sg 
    WHERE NOT EXISTS (
        SELECT 1 FROM steam_raw sr WHERE sr.appid = sg.appid
    )
""")
generico_sem_raw = cursor.fetchone()[0]
print(f'\n[2] AppIDs em steam_generico mas NAO em steam_raw: {generico_sem_raw:,}')

# 4. Verificar alguns exemplos
cursor.execute("""
    SELECT appid, name 
    FROM steam_generico sg 
    WHERE NOT EXISTS (
        SELECT 1 FROM steam_raw sr WHERE sr.appid = sg.appid
    )
    ORDER BY appid
    LIMIT 15
""")
exemplos_generico = cursor.fetchall()
print(f'\nExemplos de AppIDs faltando no steam_raw:')
for appid, nome in exemplos_generico:
    nome_truncado = (nome[:50] + '...') if nome and len(nome) > 50 else (nome or 'N/A')
    print(f'  - AppID {appid}: {nome_truncado}')

# 5. Verificar total da intersecção
cursor.execute("""
    SELECT COUNT(*) 
    FROM steam_raw sr 
    INNER JOIN steam_generico sg ON sr.appid = sg.appid
""")
interseccao = cursor.fetchone()[0]
print(f'\n[3] AppIDs presentes em AMBAS as tabelas: {interseccao:,}')

# 6. Verificar quando foram atualizadas
cursor.execute("""
    SELECT 
        MIN(ultima_atualizacao) as primeira_atualizacao,
        MAX(ultima_atualizacao) as ultima_atualizacao,
        COUNT(DISTINCT DATE(ultima_atualizacao)) as dias_distintos
    FROM steam_raw
""")
stats_raw = cursor.fetchone()
print(f'\n[4] Datas de atualização steam_raw:')
print(f'  - Primeira: {stats_raw[0]}')
print(f'  - Última: {stats_raw[1]}')
print(f'  - Dias distintos: {stats_raw[2]}')

cursor.execute("""
    SELECT 
        MIN(ultima_atualizacao) as primeira_atualizacao,
        MAX(ultima_atualizacao) as ultima_atualizacao,
        COUNT(DISTINCT DATE(ultima_atualizacao)) as dias_distintos
    FROM steam_generico
""")
stats_generico = cursor.fetchone()
print(f'\n[5] Datas de atualização steam_generico:')
print(f'  - Primeira: {stats_generico[0]}')
print(f'  - Última: {stats_generico[1]}')
print(f'  - Dias distintos: {stats_generico[2]}')

# 7. Verificar relação com itad_raw
cursor.execute("""
    SELECT 
        (SELECT COUNT(*) FROM itad_raw) as total_itad,
        (SELECT COUNT(*) FROM steam_itad_mapping) as total_mapping,
        (SELECT COUNT(*) FROM steam_itad_mapping sim 
         WHERE EXISTS (SELECT 1 FROM steam_generico sg WHERE sg.appid = sim.appid)) as mapping_com_generico,
        (SELECT COUNT(*) FROM steam_itad_mapping sim 
         WHERE NOT EXISTS (SELECT 1 FROM steam_generico sg WHERE sg.appid = sim.appid)) as mapping_sem_generico
""")
stats_itad = cursor.fetchone()
print(f'\n{"="*80}')
print("ANÁLISE ITAD")
print("="*80)
print(f'[6] Total itad_raw: {stats_itad[0]:,}')
print(f'[7] Total steam_itad_mapping: {stats_itad[1]:,}')
print(f'[8] Mappings COM AppID em steam_generico: {stats_itad[2]:,}')
print(f'[9] Mappings SEM AppID em steam_generico: {stats_itad[3]:,}')

# 8. Verificar AppIDs do mapping sem correspondência no generico
cursor.execute("""
    SELECT sim.appid, sim.title
    FROM steam_itad_mapping sim
    WHERE NOT EXISTS (SELECT 1 FROM steam_generico sg WHERE sg.appid = sim.appid)
    ORDER BY sim.appid
    LIMIT 10
""")
mapping_sem_generico = cursor.fetchall()
if mapping_sem_generico:
    print(f'\n[10] Exemplos de mappings SEM AppID no steam_generico:')
    for appid, title in mapping_sem_generico:
        title_truncado = (title[:50] + '...') if title and len(title) > 50 else (title or 'N/A')
        print(f'  - AppID {appid}: {title_truncado}')

# 9. Análise do JSON local vs banco
print(f'\n{"="*80}')
print("COMPARAÇÃO: steam_applist.json vs Banco de Dados")
print("="*80)

import json
import os

json_path = os.path.join('prj_TCC_PREVISOR_STEAM', 'resources', 'dados', 'steam_applist.json')
json_path = os.path.abspath(json_path)
if os.path.exists(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        apps_no_json = len(data.get('applist', {}).get('apps', []))
        print(f'[11] Total de AppIDs no steam_applist.json: {apps_no_json:,}')
        
        # Verificar quantos do JSON estão no generico
        appids_json = set(app['appid'] for app in data['applist']['apps'])
        
        cursor.execute("SELECT appid FROM steam_generico")
        appids_generico = set(row[0] for row in cursor.fetchall())
        
        em_ambos = len(appids_json & appids_generico)
        so_json = len(appids_json - appids_generico)
        so_generico = len(appids_generico - appids_json)
        
        print(f'[12] AppIDs em AMBOS (JSON e generico): {em_ambos:,}')
        print(f'[13] AppIDs SOMENTE no JSON: {so_json:,}')
        print(f'[14] AppIDs SOMENTE no generico: {so_generico:,}')
        
        if so_json > 0:
            exemplos_so_json = list(appids_json - appids_generico)[:10]
            print(f'\nExemplos de AppIDs do JSON que faltam no generico:')
            for appid in sorted(exemplos_so_json):
                app_info = next((app for app in data['applist']['apps'] if app['appid'] == appid), None)
                if app_info:
                    nome = app_info.get('name', 'N/A')
                    nome_truncado = (nome[:50] + '...') if len(nome) > 50 else nome
                    print(f'  - AppID {appid}: {nome_truncado}')
else:
    print('[11] Arquivo steam_applist.json não encontrado!')

print(f'\n{"="*80}')
print("RESUMO")
print("="*80)
print(f'steam_raw tem {raw_sem_generico:,} AppIDs a mais que steam_generico')
print(f'steam_generico tem {generico_sem_raw:,} AppIDs a mais que steam_raw')
print(f'Intersecção: {interseccao:,} AppIDs')
print(f'ITAD mapping sem correspondência no generico: {stats_itad[3]:,}')
print("="*80)

cursor.close()
conn.close()
