"""
Script para verificar quantidade de registros e primeiros itens de cada tabela.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

def check_database_status():
    """Verifica status de todas as tabelas no banco PostgreSQL."""
    
    print("\n" + "="*80)
    print("STATUS DO BANCO DE DADOS POSTGRESQL (Docker)")
    print("="*80 + "\n")
    
    db = PostgreSQL()
    
    try:
        # Conecta ao banco
        db.conectar()
        conn = db._var_connConnection
        
        if not conn or conn.closed:
            print("[ERRO] Não foi possível estabelecer conexão ao banco de dados")
            return
        
        cursor = conn.cursor()
        
        # Lista de tabelas para verificar
        tabelas = [
            'steam_raw',
            'steam_bd',
            'steam_generico',
            'steam_unificado',
            'itad_raw',
            'steam_itad_mapping'
        ]
        
        for tabela in tabelas:
            print(f"\n{'='*80}")
            print(f"TABELA: {tabela}")
            print(f"{'='*80}")
            
            try:
                # Conta total de registros
                cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                total = cursor.fetchone()[0]
                print(f"\n[Total de registros]: {total:,}")
                
                if total > 0:
                    # Busca os 10 primeiros registros
                    if tabela == 'steam_raw':
                        cursor.execute(f"""
                            SELECT appid, ultima_atualizacao 
                            FROM {tabela} 
                            ORDER BY appid 
                            LIMIT 10
                        """)
                        print(f"\n[Primeiros 10 registros]:")
                        print(f"{'AppID':<10} {'Última Atualização':<25}")
                        print("-" * 80)
                        for row in cursor.fetchall():
                            appid, data = row
                            data_str = data.strftime('%Y-%m-%d %H:%M:%S') if data else 'N/A'
                            print(f"{appid:<10} {data_str:<25}")
                    
                    elif tabela == 'steam_bd':
                        cursor.execute(f"""
                            SELECT appid, nome, type, preco, data_lancamento 
                            FROM {tabela} 
                            ORDER BY appid 
                            LIMIT 10
                        """)
                        print(f"\n[Primeiros 10 registros]:")
                        print(f"{'AppID':<10} {'Nome':<35} {'Type':<15} {'Preço':<10} {'Lançamento':<12}")
                        print("-" * 80)
                        for row in cursor.fetchall():
                            appid, nome, tipo, preco, data_lanc = row
                            nome_truncado = (nome[:32] + '...') if nome and len(nome) > 35 else (nome or 'N/A')
                            tipo_str = (tipo[:12] + '...') if tipo and len(tipo) > 15 else (tipo or 'N/A')
                            # Converter preco para float se for string
                            if isinstance(preco, str):
                                try:
                                    preco = float(preco)
                                except (ValueError, TypeError):
                                    preco = None
                            preco_str = f"R$ {preco:.2f}" if preco else 'Grátis'
                            # Tratar data como string ou date
                            if isinstance(data_lanc, str):
                                data_str = data_lanc[:10] if data_lanc else 'N/A'
                            else:
                                data_str = data_lanc.strftime('%Y-%m-%d') if data_lanc else 'N/A'
                            print(f"{appid:<10} {nome_truncado:<35} {tipo_str:<15} {preco_str:<10} {data_str:<12}")
                    
                    elif tabela == 'steam_generico':
                        cursor.execute(f"""
                            SELECT appid, name, ultima_atualizacao 
                            FROM {tabela} 
                            ORDER BY appid 
                            LIMIT 10
                        """)
                        print(f"\n[Primeiros 10 registros]:")
                        print(f"{'AppID':<10} {'Name':<50} {'Última Atualização':<25}")
                        print("-" * 80)
                        for row in cursor.fetchall():
                            appid, nome, data = row
                            nome_truncado = (nome[:47] + '...') if nome and len(nome) > 50 else (nome or 'N/A')
                            data_str = data.strftime('%Y-%m-%d %H:%M:%S') if data else 'N/A'
                            print(f"{appid:<10} {nome_truncado:<50} {data_str:<25}")
                    
                    elif tabela == 'steam_unificado':
                        cursor.execute(f"""
                            SELECT appid, nome, type, preco, data_lancamento, total_positive, total_negative 
                            FROM {tabela} 
                            ORDER BY appid 
                            LIMIT 10
                        """)
                        print(f"\n[Primeiros 10 registros]:")
                        print(f"{'AppID':<10} {'Nome':<30} {'Type':<12} {'Preço':<10} {'Lançam.':<12} {'Reviews':<15}")
                        print("-" * 80)
                        for row in cursor.fetchall():
                            appid, nome, tipo, preco, data_lanc, pos, neg = row
                            nome_truncado = (nome[:27] + '...') if nome and len(nome) > 30 else (nome or 'N/A')
                            tipo_str = (tipo[:9] + '...') if tipo and len(tipo) > 12 else (tipo or 'N/A')
                            # Converter preco para float se for string
                            if isinstance(preco, str):
                                try:
                                    preco = float(preco)
                                except (ValueError, TypeError):
                                    preco = None
                            preco_str = f"R$ {preco:.2f}" if preco else 'Grátis'
                            # Tratar data como string ou date
                            if isinstance(data_lanc, str):
                                data_str = data_lanc[:10] if data_lanc else 'N/A'
                            else:
                                data_str = data_lanc.strftime('%Y-%m-%d') if data_lanc else 'N/A'
                            reviews_str = f"+{pos or 0}/-{neg or 0}"
                            print(f"{appid:<10} {nome_truncado:<30} {tipo_str:<12} {preco_str:<10} {data_str:<12} {reviews_str:<15}")
                    
                    elif tabela == 'itad_raw':
                        cursor.execute(f"""
                            SELECT slug, title, type, id_itad 
                            FROM {tabela} 
                            ORDER BY slug 
                            LIMIT 10
                        """)
                        print(f"\n[Primeiros 10 registros]:")
                        print(f"{'Slug':<25} {'Title':<40} {'Type':<12} {'ITAD ID':<30}")
                        print("-" * 80)
                        for row in cursor.fetchall():
                            slug, title, tipo, itad_id = row
                            slug_str = (slug[:22] + '...') if slug and len(slug) > 25 else (slug or 'N/A')
                            title_str = (title[:37] + '...') if title and len(title) > 40 else (title or 'N/A')
                            tipo_str = (tipo[:9] + '...') if tipo and len(tipo) > 12 else (tipo or 'N/A')
                            itad_str = (itad_id[:27] + '...') if itad_id and len(itad_id) > 30 else (itad_id or 'N/A')
                            print(f"{slug_str:<25} {title_str:<40} {tipo_str:<12} {itad_str:<30}")
                    
                    elif tabela == 'steam_itad_mapping':
                        cursor.execute(f"""
                            SELECT appid, id_itad, slug, title 
                            FROM {tabela} 
                            ORDER BY appid 
                            LIMIT 10
                        """)
                        print(f"\n[Primeiros 10 registros]:")
                        print(f"{'AppID':<10} {'ID ITAD':<30} {'Slug':<25} {'Title':<30}")
                        print("-" * 80)
                        for row in cursor.fetchall():
                            appid, itad_id, slug, title = row
                            itad_str = (itad_id[:27] + '...') if itad_id and len(itad_id) > 30 else (itad_id or 'N/A')
                            slug_str = (slug[:22] + '...') if slug and len(slug) > 25 else (slug or 'N/A')
                            title_str = (title[:27] + '...') if title and len(title) > 30 else (title or 'N/A')
                            print(f"{appid:<10} {itad_str:<30} {slug_str:<25} {title_str:<30}")
                
                else:
                    print("\n[Tabela vazia - sem registros]")
                    
            except Exception as e:
                print(f"\n[ERRO ao consultar tabela {tabela}]: {e}")
        
        print(f"\n{'='*80}")
        print("RESUMO GERAL")
        print(f"{'='*80}\n")
        
        # Resumo geral
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                total = cursor.fetchone()[0]
                print(f"  {tabela:<25} : {total:>10,} registros")
            except:
                print(f"  {tabela:<25} : [ERRO]")
        
        print(f"\n{'='*80}\n")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n[ERRO GERAL]: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_database_status()
