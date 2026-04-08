"""
Script de validação para configuração Multi-PC
Verifica se o ambiente está correto antes de executar o bot principal.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

def print_status(msg, status):
    """Imprime status com emoji"""
    emoji = "✅" if status else "❌"
    print(f"{emoji} {msg}")
    return status

def validar_ambiente():
    """Valida configuração do ambiente"""
    print("\n" + "="*60)
    print("🔍 VALIDAÇÃO DE CONFIGURAÇÃO MULTI-PC")
    print("="*60 + "\n")
    
    erros = []
    
    # 1. Verificar variáveis de ambiente
    print("📋 Variáveis de Ambiente:")
    pc_id = os.getenv("PC_ID")
    total_pcs = os.getenv("TOTAL_PCS")
    
    if not print_status(f"PC_ID encontrado: {pc_id}", pc_id):
        erros.append("PC_ID não definido no .env")
    
    if not print_status(f"TOTAL_PCS encontrado: {total_pcs}", total_pcs):
        erros.append("TOTAL_PCS não definido no .env")
    
    if pc_id and total_pcs:
        pc_id = int(pc_id)
        total_pcs = int(total_pcs)
        
        if pc_id < 1 or pc_id > total_pcs:
            print_status(f"PC_ID ({pc_id}) deve estar entre 1 e {total_pcs}", False)
            erros.append(f"PC_ID inválido: {pc_id}")
        else:
            print_status(f"Configuração: PC {pc_id} de {total_pcs}", True)
    
    print()
    
    # 2. Verificar PostgreSQL (Docker)
    print("🐳 PostgreSQL (Docker):")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        print_status("Conexão PostgreSQL estabelecida", True)
        
        # Verificar tabelas
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM steam_generico;")
        count_generico = cursor.fetchone()[0]
        print_status(f"Tabela steam_generico: {count_generico:,} registros", count_generico > 0)
        
        if count_generico == 0:
            erros.append("Tabela steam_generico está vazia! Popule com dados da Steam API.")
        
        try:
            cursor.execute("SELECT COUNT(*) FROM steam_raw;")
            count_raw = cursor.fetchone()[0]
            print_status(f"Tabela steam_raw: {count_raw:,} registros", True)
        except:
            print_status("Tabela steam_raw não existe (será criada automaticamente)", True)
        
        conn.close()
        
    except Exception as e:
        print_status(f"Erro ao conectar PostgreSQL: {e}", False)
        erros.append(f"PostgreSQL: {e}")
    
    print()
    
    # 3. Verificar configurações de processamento
    print("⚙️ Configurações de Processamento:")
    ambiente = os.getenv("AMBIENTE", "PRD")
    batch_size = os.getenv("RANGE_PROCESSAMENTO_APPIDS_RAW", "1000")
    
    print_status(f"Ambiente: {ambiente}", True)
    print_status(f"Batch size: {batch_size} AppIDs por lote", True)
    
    if ambiente == "HML":
        batch_teste = os.getenv("BATCH_TESTE", "20")
        print(f"   ⚠️ Modo teste: apenas {batch_teste} AppIDs serão processados")
    
    print()
    
    # 5. Resumo final
    print("="*60)
    if erros:
        print("❌ VALIDAÇÃO FALHOU - Erros encontrados:")
        for erro in erros:
            print(f"   • {erro}")
        print("\n📖 Consulte: TRANSFERENCIA_PC2.md")
        return False
    else:
        print("✅ VALIDAÇÃO COMPLETA - Sistema pronto para executar!")
        print(f"\n🚀 Execute: python prj_TCC_PREVISOR_STEAM/bot.py")
        
        if total_pcs and int(total_pcs) > 1:
            print(f"\n💡 Este é o PC {pc_id} de {total_pcs}")
            if int(pc_id) == 1:
                print("   • Processará AppIDs PARES (10, 20, 30...)")
            else:
                print("   • Processará AppIDs ÍMPARES (11, 21, 31...)")
        
        return True

if __name__ == "__main__":
    sucesso = validar_ambiente()
    sys.exit(0 if sucesso else 1)
