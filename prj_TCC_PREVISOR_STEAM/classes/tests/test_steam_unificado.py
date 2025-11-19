"""Teste rápido dos novos métodos steam_unificado"""
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

# Teste 1: Buscar um registro
print("=" * 60)
print("TESTE 1: Buscar AppID 10")
print("=" * 60)
dados = PostgreSQL.buscar_steam_unificado(10)
if dados:
    print(f"✓ AppID: {dados['appid']}")
    print(f"✓ Nome: {dados['nome']}")
    print(f"✓ Type: {dados['type']}")
    print(f"✓ Preço: {dados['preco']}")
    print(f"✓ Reviews: {dados['total_reviews']}")
    print(f"✓ Tem detalhes JSONB: {dados['detalhes_completos'] is not None}")
    print(f"✓ Tem reviews JSONB: {dados['reviews_completos'] is not None}")
else:
    print("✗ Nenhum dado encontrado")

# Teste 2: Buscar múltiplos registros
print("\n" + "=" * 60)
print("TESTE 2: Buscar 3 registros")
print("=" * 60)
todos = PostgreSQL.buscar_todos_steam_unificado(3)
print(f"✓ Total encontrado: {len(todos)}")
for jogo in todos:
    print(f"  - {jogo['appid']}: {jogo['nome']} ({jogo['type']})")

# Teste 3: Inserir/Atualizar um registro
print("\n" + "=" * 60)
print("TESTE 3: Inserir/Atualizar registro teste")
print("=" * 60)
dados_teste = {
    'appid': 999999,
    'nome': 'Jogo Teste Unificado',
    'type': 'game',
    'preco': 'R$ 29,90',
    'total_reviews': 100,
    'review_score': 85,
    'detalhes_completos': {'test': True, 'version': '1.0'},
    'reviews_completos': {'positive': 85, 'negative': 15}
}

try:
    PostgreSQL.inserir_steam_unificado(dados_teste)
    print("✓ Registro inserido com sucesso")
    
    # Busca para confirmar
    verificar = PostgreSQL.buscar_steam_unificado(999999)
    if verificar:
        print(f"✓ Verificação OK: {verificar['nome']}")
    else:
        print("✗ Erro: registro não encontrado após inserção")
except Exception as e:
    print(f"✗ Erro: {e}")

print("\n" + "=" * 60)
print("TESTES CONCLUÍDOS")
print("=" * 60)
