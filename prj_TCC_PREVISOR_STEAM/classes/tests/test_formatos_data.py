"""
Teste dos novos formatos de data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL

# Formatos que estavam dando warning
var_listDatasTestar = [
    "22/fev./2018",
    "1/fev./2018",
    "1/mai./2017",
    "30/ago./2016",
    "18/abr./2021",
    "19/out./2017",
    "6/dez./2016",
    "16/abr./2019",
    "25/out./2016",
    "4º trimestre de 2026",
    "7/abr./2017",
    "5/abr./2016",
    "22/set./2016",
    "Em breve",
    "A ser anunciada",
    "1/nov./2000",  # Este já funcionava
]

print("\n" + "=" * 80)
print("TESTE DE FORMATOS DE DATA")
print("=" * 80 + "\n")

var_intOk = 0
var_intVazio = 0
var_intErro = 0

for var_strData in var_listDatasTestar:
    try:
        var_strResultado = ProcessadorETL.processar_data_lancamento(var_strData)
        
        if var_strResultado:
            print(f"OK:    '{var_strData}' -> '{var_strResultado}'")
            var_intOk += 1
        else:
            print(f"VAZIO: '{var_strData}' -> (vazio - esperado para textos descritivos)")
            var_intVazio += 1
    except Exception as e:
        print(f"ERRO:  '{var_strData}' -> {e}")
        var_intErro += 1

print("\n" + "=" * 80)
print("RESUMO:")
print(f"  Convertidas com sucesso: {var_intOk}")
print(f"  Vazias (esperado): {var_intVazio}")
print(f"  Erros: {var_intErro}")
print("=" * 80 + "\n")
