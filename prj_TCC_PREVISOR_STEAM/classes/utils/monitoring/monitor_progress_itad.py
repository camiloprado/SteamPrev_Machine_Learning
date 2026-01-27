from prj_TCC_PREVISOR_STEAM.classes.core.application import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.database import PostgreSQL
import time
import os

def monitor_progress():
    """
    Monitora o progresso do processamento ITAD em tempo real.
    """
    print("\n" + "=" * 70)
    print("MONITOR DE PROGRESSO - REPROCESSAMENTO ITAD")
    print("=" * 70)
    print("\nPressione Ctrl+C para sair\n")
    
    var_intTotalInicial = 266595  # Total inicial sem ITAD
    var_intAnterior = None
    var_intIteracao = 0
    
    try:
        while True:
            PostgreSQL.conectar()
            
            with PostgreSQL._var_connConnection.cursor() as cursor:
                # Total em steam_generico
                cursor.execute("SELECT COUNT(*) FROM steam_generico")
                var_intTotalGenerico = cursor.fetchone()[0]
                
                # Com ITAD
                cursor.execute("SELECT COUNT(*) FROM steam_itad_mapping")
                var_intComITAD = cursor.fetchone()[0]
                
                # itad_raw
                cursor.execute("SELECT COUNT(*) FROM itad_raw")
                var_intITADRaw = cursor.fetchone()[0]
                
                # Sem ITAD
                var_intSemITAD = var_intTotalGenerico - var_intComITAD
            
            PostgreSQL.desconectar()
            
            # Calcula progresso
            var_intProcessados = var_intTotalInicial - var_intSemITAD
            var_floatPercent = (var_intProcessados / var_intTotalInicial) * 100
            
            # Calcula velocidade
            if var_intAnterior is not None:
                var_intDelta = var_intAnterior - var_intSemITAD
                var_floatVelocidade = var_intDelta / 30  # AppIDs por segundo (30s interval)
            else:
                var_floatVelocidade = 0
            
            # Limpa tela (Windows)
            if var_intIteracao > 0:
                os.system('cls' if os.name == 'nt' else 'clear')
            
            print("\n" + "=" * 70)
            print("MONITOR DE PROGRESSO - REPROCESSAMENTO ITAD")
            print("=" * 70)
            
            print(f"\n📊 ESTATÍSTICAS:")
            print(f"   Total em steam_generico:    {var_intTotalGenerico:>10,}")
            print(f"   Com ITAD (mapping):         {var_intComITAD:>10,}")
            print(f"   itad_raw:                   {var_intITADRaw:>10,}")
            print(f"   Sem ITAD (restantes):       {var_intSemITAD:>10,}")
            
            print(f"\n📈 PROGRESSO:")
            print(f"   Processados:                {var_intProcessados:>10,} / {var_intTotalInicial:,}")
            print(f"   Percentual:                 {var_floatPercent:>10.2f}%")
            
            # Barra de progresso
            var_intBarra = int(var_floatPercent / 2)
            var_strBarra = "█" * var_intBarra + "░" * (50 - var_intBarra)
            print(f"   [{var_strBarra}]")
            
            if var_floatVelocidade > 0:
                print(f"\n⚡ VELOCIDADE:")
                print(f"   AppIDs/segundo:             {var_floatVelocidade:>10.2f}")
                print(f"   AppIDs/minuto:              {var_floatVelocidade * 60:>10,.0f}")
                
                # Tempo restante estimado
                var_intMinutosRestantes = int(var_intSemITAD / (var_floatVelocidade * 60))
                var_intHoras = var_intMinutosRestantes // 60
                var_intMinutos = var_intMinutosRestantes % 60
                print(f"   Tempo estimado:             {var_intHoras:>10}h {var_intMinutos:02d}min")
            
            print(f"\n🕐 Última atualização: {time.strftime('%H:%M:%S')}")
            print("   (Atualiza a cada 30 segundos)")
            print("\nPressione Ctrl+C para sair")
            
            var_intAnterior = var_intSemITAD
            var_intIteracao += 1
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n✓ Monitor encerrado pelo usuário")
    except Exception as e:
        print(f"\n\n✗ Erro no monitor: {e}")
    finally:
        try:
            PostgreSQL.desconectar()
        except:
            pass

if __name__ == "__main__":
    monitor_progress()
