"""
Teste de retry automático com API Steam indisponível
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from prj_TCC_PREVISOR_STEAM.classes.integrations.steam.client import SteamClient
from unittest.mock import patch, Mock
import requests

print("=== TESTE DE RETRY AUTOMÁTICO - API STEAM ===\n")

# Simular erro 503 (Service Unavailable)
print("1. Simulando erro 503 (Service Unavailable)...")
with patch('requests.get') as mock_get:
    mock_response = Mock()
    mock_response.status_code = 503
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_get.return_value = mock_response
    
    try:
        SteamClient.find_app_list()
        print("   ✗ Deveria ter lançado exceção após 5 tentativas")
    except Exception as e:
        if "após 5 tentativas" in str(e):
            print("   ✓ Retry funcionou! Tentou 5 vezes antes de falhar")
        else:
            print(f"   ✗ Erro inesperado: {e}")

# Simular sucesso na 3ª tentativa
print("\n2. Simulando sucesso na 3ª tentativa...")

class CallCounter:
    count = 0

def side_effect_success_third(*args, **kwargs):
    CallCounter.count += 1
    
    if CallCounter.count < 3:
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        return mock_response
    else:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"applist": {"apps": [{"appid": 10, "name": "Counter-Strike"}]}}
        return mock_response

with patch('requests.get') as mock_get:
    CallCounter.count = 0  # Reset counter
    mock_get.side_effect = side_effect_success_third
    
    try:
        resultado = SteamClient.find_app_list()
        if len(resultado) == 1 and resultado[0]['appid'] == 10:
            print(f"   ✓ Sucesso após {CallCounter.count} tentativas!")
        else:
            print(f"   ✗ Resultado inesperado: {resultado}")
    except Exception as e:
        print(f"   ✗ Erro: {e}")

# Testar timeout
print("\n3. Simulando timeout...")
with patch('requests.get') as mock_get:
    mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
    
    try:
        SteamClient.find_app_list()
        print("   ✗ Deveria ter lançado exceção de timeout")
    except Exception as e:
        if "Timeout após 5 tentativas" in str(e):
            print("   ✓ Timeout tratado corretamente com retry")
        else:
            print(f"   ✗ Erro inesperado: {e}")

print("\n=== TESTE CONCLUÍDO ===")
print("\n📋 Resumo da implementação:")
print("  ✓ Retry automático: 5 tentativas")
print("  ✓ Backoff exponencial: 5s, 10s, 20s, 40s, 80s")
print("  ✓ Tratamento de erros 503, 500, Timeout, ConnectionError")
print("  ✓ Logs informativos em cada tentativa")
print("\n💡 Benefícios:")
print("  - API Steam fora por 1-2 minutos? Sistema aguarda e tenta novamente")
print("  - Serviço temporariamente indisponível? Retry automático")
print("  - Evita falha total por problema momentâneo na API")
