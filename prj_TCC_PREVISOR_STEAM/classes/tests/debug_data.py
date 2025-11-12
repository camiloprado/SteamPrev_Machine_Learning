"""
Debug do processamento de data
"""

import re

var_strData = "22/fev./2018"

print(f"Original: '{var_strData}'")

# Passo 1: Remove pontos após abreviações
var_strLimpa = re.sub(r'([a-z]{3})\.', r'\1', var_strData, flags=re.IGNORECASE)
print(f"Após regex: '{var_strLimpa}'")

# Passo 2: Remove pontos restantes
var_strLimpa = var_strLimpa.replace('.', '')
print(f"Sem pontos: '{var_strLimpa}'")

# Passo 3: Normaliza espaços
var_strLimpa = ' '.join(var_strLimpa.split())
print(f"Final: '{var_strLimpa}'")

# Testa se contém caractere º
print(f"\nContém 'º': {'º' in var_strData}")
print(f"Encoding do º: {ord('º')}")
