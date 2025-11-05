"""
Script para verificar dados no Supabase - steam_raw vs steam_bd
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
load_dotenv()

from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

def main():
    print("=" * 60)
    print("📊 COMPARAÇÃO: steam_raw vs steam_bd")
    print("=" * 60)
    
    try:
        # Conecta
        print("\n🔌 Conectando ao Supabase...")
        SupabaseDB.conectar()
        
        # Obtém estatísticas
        stats = SupabaseDB.obter_estatisticas()
        
        print(f"\n{'='*60}")
        print(f"📊 ESTATÍSTICAS")
        print(f"{'='*60}")
        print(f"📦 steam_raw (dados brutos):     {stats['total_raw']:,} registros")
        print(f"🎮 steam_bd (dados processados): {stats['total_bd']:,} registros")
        print(f"📈 Diferença:                    {stats['diferenca']:,} registros")
        print(f"{'='*60}")
        
        # Explica a diferença
        print(f"\n💡 O QUE SIGNIFICA:")
        print(f"   • steam_raw: Dados coletados da API Steam (detalhes + reviews)")
        print(f"   • steam_bd: Dados processados e limpos prontos para análise")
        print(f"   • Diferença: {stats['diferenca']} jogos ainda não foram processados")
        
        # Busca alguns exemplos de steam_raw
        print(f"\n📋 EXEMPLOS de registros em steam_raw:")
        registros_raw = SupabaseDB.buscar_todos_dadosSteamRaw(arg_intLimit=5)
        
        if registros_raw:
            for i, reg in enumerate(registros_raw, 1):
                appid = reg.get('appid')
                tem_detalhes = "✅" if reg.get('detalhes') else "❌"
                tem_reviews = "✅" if reg.get('reviews') else "❌"
                print(f"   {i}. AppID {appid}: Detalhes {tem_detalhes} | Reviews {tem_reviews}")
        
        # Busca alguns exemplos de steam_bd
        print(f"\n🎮 EXEMPLOS de registros em steam_bd:")
        registros_bd = SupabaseDB.buscar_todos_dadosSteamBD(arg_intLimit=5)
        
        if registros_bd:
            for i, reg in enumerate(registros_bd, 1):
                appid = reg.get('appid')
                nome = reg.get('nome', 'N/A')
                print(f"   {i}. AppID {appid}: {nome}")
        else:
            print("   ℹ️ Nenhum registro encontrado (ainda não processados)")
        
        print(f"\n{'='*60}")
        print("✅ Verificação concluída!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🔌 Desconectando...")
        SupabaseDB.desconectar()


if __name__ == "__main__":
    main()
