"""
Script para verificar o que foi salvo no Supabase
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
load_dotenv()

from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

def verificar_dados():
    """
    Verifica os dados no Supabase
    """
    
    print("=" * 60)
    print("📊 VERIFICANDO DADOS NO SUPABASE")
    print("=" * 60)
    
    try:
        # Conecta
        print("\n🔌 Conectando ao Supabase...")
        SupabaseDB.conectar()
        
        # Obtém estatísticas
        print("\n📈 Obtendo estatísticas...")
        stats = SupabaseDB.obter_estatisticas()
        
        print(f"\n{'='*60}")
        print(f"📊 ESTATÍSTICAS DO BANCO")
        print(f"{'='*60}")
        print(f"📦 Total em steam_raw:  {stats['total_raw']:,} registros")
        print(f"🎮 Total em steam_bd:   {stats['total_bd']:,} registros")
        print(f"📈 Diferença:           {stats['diferenca']:,} registros")
        print(f"{'='*60}")
        
        # Lista alguns registros
        print(f"\n📋 Últimos registros em steam_raw:")
        registros = SupabaseDB.buscar_todos_dadosSteamRaw(arg_intLimit=10)
        
        if registros:
            print(f"\n{'AppID':<10} | {'Tem Detalhes':<15} | {'Tem Reviews':<15}")
            print("-" * 50)
            for reg in registros:
                appid = reg.get('appid', 'N/A')
                tem_detalhes = "✅ Sim" if reg.get('detalhes') else "❌ Não"
                tem_reviews = "✅ Sim" if reg.get('reviews') else "❌ Não"
                print(f"{appid:<10} | {tem_detalhes:<15} | {tem_reviews:<15}")
        else:
            print("   ℹ️ Nenhum registro encontrado")
        
        print("\n" + "="*60)
        print("✅ Verificação concluída!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Desconecta
        print("\n🔌 Desconectando...")
        SupabaseDB.desconectar()


if __name__ == "__main__":
    verificar_dados()
