from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL

PostgreSQL.conectar()

with PostgreSQL._var_connConnection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'itad_raw' 
        ORDER BY ordinal_position
    """)
    columns = [row[0] for row in cursor.fetchall()]
    
print(f"Colunas de itad_raw: {columns}")

# Verificar alguns registros
with PostgreSQL._var_connConnection.cursor() as cursor:
    cursor.execute("SELECT * FROM itad_raw LIMIT 3")
    rows = cursor.fetchall()
    
    print(f"\nPrimeiros 3 registros:")
    for row in rows:
        print(row)

PostgreSQL.desconectar()
