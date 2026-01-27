from prj_TCC_PREVISOR_STEAM.classes.data.database import PostgreSQL

PostgreSQL.conectar()

cursor = PostgreSQL._var_connConnection.cursor()
cursor.execute('SELECT appid FROM steam_raw WHERE appid = 1099410')
resultado = cursor.fetchone()

print(f'AppID 1099410 existe em steam_raw: {resultado is not None}')
if resultado:
    print(f'AppID encontrado: {resultado[0]}')
else:
    print('AppID 1099410 NÃO foi encontrado')

PostgreSQL.desconectar()
