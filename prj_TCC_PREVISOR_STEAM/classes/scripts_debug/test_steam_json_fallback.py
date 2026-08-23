"""
Testa o fallback para arquivo JSON local quando a API Steam retorna 404.

Nota: find_app_list()/load_app_list() foram movidos de SteamClient (steam_api.py)
para LocalClient (local_steam.py). Este script foi atualizado para refletir isso.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from prj_TCC_PREVISOR_STEAM.classes.api.local_steam import LocalClient

print("\n" + "="*80)
print("TESTE: Carregamento com fallback para steam_applist.json")
print("="*80 + "\n")

try:
    # Força reload para testar o fallback
    print("[DEBUG] Chamando LocalClient.load_app_list()...")
    apps = LocalClient.load_app_list(arg_boolForce=True)
    print(f"[DEBUG] Retorno: {type(apps)}, len={len(apps) if apps else 0}")
    
    if apps:
        print(f"\n[OK] SUCESSO! Total de AppIDs carregados: {len(apps):,}\n")
        print("Primeiros 5 apps:")
        for i, app in enumerate(apps[:5], 1):
            appid = app.get('appid', 'N/A')
            name = app.get('name', 'N/A')[:60]
            print(f"   {i}. AppID {appid:>8} - {name}")
        
        print("\n" + "="*80)
        print("[OK] O fallback para JSON local funcionou!")
        print("="*80)
    else:
        print("\n[ERRO] Nenhum AppID foi carregado (lista vazia ou None)")
        
except Exception as e:
    print(f"\n[ERRO] Excecao: {e}")
    import traceback
    traceback.print_exc()
