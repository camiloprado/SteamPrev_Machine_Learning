"""
Arquivo de configuração do pytest para a pasta de testes.
"""

import pytest
import os
import sys

# Adiciona o diretório principal ao sys.path para facilitar imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Fixtures globais podem ser definidas aqui
@pytest.fixture(scope="session")
def setup_env():
    """
    Fixture para carregar variáveis de ambiente e preparar contexto global.
    """
    from dotenv import load_dotenv
    load_dotenv()
    yield
