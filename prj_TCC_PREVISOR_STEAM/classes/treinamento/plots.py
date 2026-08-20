import os
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger("treino.plots")

class Plots:
    @classmethod
    def _obter_diretorio_relatorios(cls) -> Path:
        """
        Obtém o diretório padrão do projeto para relatórios (resources/relatorios).
        
        Retorna:
        - Path: Objeto Path do diretório de relatórios, garantindo que exista.
        """
        var_pathBase = Path(__file__).resolve().parents[2]
        
        # Constrói caminho até resources/relatorios
        var_pathRelatorios = var_pathBase / "resources" / "relatorios"
        
        # Cria a pasta se não existir (mkdir com parents=True faz criação em cascata)
        var_pathRelatorios.mkdir(parents=True, exist_ok=True)
        
        # Retorna o Path object (pode usar para salvar arquivos)
        return var_pathRelatorios


    @staticmethod
    def _obter_config_plots(arg_strTipo: str = "matriz_confusao") -> tuple[bool, bool, int]:
        """Define se deve gerar plot baseado no tipo.

        Parâmetros:
        - arg_strTipo: "matriz_confusao" ou "regressao"

        Retorna:
        - (salvar_png, mostrar, dpi)
        """
        if arg_strTipo == "regressao":
            var_strMode = (os.getenv("REGRESSAO_PLOT", "") or "").strip().lower()
            var_strDpi = (os.getenv("REGRESSAO_PLOT_DPI", "") or "").strip()
        else:
            var_strMode = (os.getenv("MATRIZ_CONFUSAO_PLOT", "") or "").strip().lower()
            var_strDpi = (os.getenv("MATRIZ_CONFUSAO_PLOT_DPI", "") or "").strip()

        # Define DPI padrão em 300
        var_intDpi = 300
        try:
            # Tenta converter DPI da variável de ambiente para inteiro
            if var_strDpi:
                var_intDpi = int(var_strDpi)
        except Exception:
            # Se falhar, mantém 300 como padrão
            var_intDpi = 300

        # Verifica cada modo possível e retorna configuração apropriada
        if var_strMode in ("", "0", "false", "no", "nao"):
            # Não salva, não mostra
            return (False, False, var_intDpi)

        if var_strMode in ("show", "mostrar"):
            # Mostra na tela, mas não salva (útil para debugging)
            return (False, True, var_intDpi)

        if var_strMode in ("both", "save_show", "save+show", "salvar_mostrar"):
            # Salva PNG E mostra na tela (útil para análise imediata)
            return (True, True, var_intDpi)

        # Modo padrão: salva PNG com qualidade DPI, não mostra
        # (melhor para processamento em lote, evita bloquear execução)
        return (True, False, var_intDpi)


    @classmethod
    def _plot_confusion_matrix(cls, arg_strModelo: str, arg_strSplit: str, arg_arrCounts, arg_arrNorm, arg_listLabelNames, arg_strTs: str, arg_boolSalvarPng: bool, arg_boolMostrar: bool, arg_intDpi: int) -> None:
        """
        Gera um plot da matriz de confusão (heatmap) via Matplotlib.

        Parâmetros:
        - arg_strModelo (str): Nome do modelo para contextualizar o título do plot.
        - arg_strSplit (str): Identificador do split (ex: "teste", "treino") para contextualizar o título do plot.
        - arg_arrCounts (array-like): Matriz de confusão com contagens absolutas.
        - arg_arrNorm (array-like): Matriz de confusão normalizada (por exemplo, por linha).
        - arg_listLabelNames (list): Lista de nomes para os rótulos/classes, usada nos ticks do plot.
        - arg_strTs (str): Timestamp para contextualizar o título do plot e nome do arquivo.
        - arg_boolSalvarPng (bool): Se True, salva o plot como PNG em resources/relatorios.
        - arg_boolMostrar (bool): Se True, exibe o plot na tela.
        - arg_intDpi (int): DPI para salvar o PNG (se arg_boolSalvarPng for True).

        Retorna:
        """
        try:
            # Se vamos apenas salvar (sem mostrar), garante backend não-interativo.
            if arg_boolSalvarPng and not arg_boolMostrar:
                import matplotlib

                matplotlib.use("Agg")

            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            logger.warning(f"Matplotlib indisponível para plotar matriz de confusão ({arg_strModelo}): {e}")
            return

        try:
            var_arrCounts = np.asarray(arg_arrCounts)
            var_arrNorm = np.asarray(arg_arrNorm)
            var_intN = int(var_arrCounts.shape[0])
            var_strFigSize = os.getenv("MATRIZ_CONFUSAO_PLOT_FIGSIZE", "7.5,6.0").split(",")
            var_objFig, var_objAxes = plt.subplots(figsize=(float(var_strFigSize[0]), float(var_strFigSize[1])), dpi=max(72, int(arg_intDpi)))
            var_objImage = var_objAxes.imshow(var_arrNorm, interpolation="nearest", cmap="Blues", vmin=0.0, vmax=1.0)
            var_objAxes.figure.colorbar(var_objImage, ax=var_objAxes, fraction=0.046, pad=0.04)

            var_objAxes.set(
                xticks=list(range(var_intN)),
                yticks=list(range(var_intN)),
                xticklabels=arg_listLabelNames,
                yticklabels=arg_listLabelNames,
                ylabel="Verdadeiro",
                xlabel="Predito",
                title=f"Matriz de Confusão - {arg_strModelo} ({arg_strSplit})",
            )

            plt.setp(var_objAxes.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor")

            # Anotações: contagem + porcentagem (normalizada por linha)
            for var_intI in range(var_intN):
                for var_intJ in range(var_intN):
                    var_intCount = int(var_arrCounts[var_intI, var_intJ])
                    try:
                        var_floatPct = float(var_arrNorm[var_intI, var_intJ])
                    except Exception:
                        var_floatPct = 0.0

                    var_strText = f"{var_intCount:,}\n({var_floatPct:.1%})"
                    var_strColor = "white" if var_floatPct >= 0.50 else "black"
                    var_objAxes.text(var_intJ, var_intI, var_strText, ha="center", va="center", color=var_strColor, fontsize=8)

            var_objFig.tight_layout()

            if arg_boolSalvarPng:
                var_pathRelatorios = Plots._obter_diretorio_relatorios()
                var_strBaseName = f"confusion_{arg_strModelo}_{arg_strSplit}_{arg_strTs}"
                var_pathPng = var_pathRelatorios / f"{var_strBaseName}_plot.png"
                var_objFig.savefig(var_pathPng, dpi=max(72, int(arg_intDpi)))
                logger.info(f"PNG matriz de confusão salvo: {var_pathPng}")

            if arg_boolMostrar:
                plt.show()
        except Exception as e:
            logger.warning(f"Falha ao gerar plot da matriz de confusão ({arg_strModelo}): {e}")
        finally:
            try:
                plt.close("all")
            except Exception:
                pass


    @classmethod
    def _plot_regressao_predito_vs_real(cls, arg_strModelo: str, arg_arrYReal, arg_arrYPred, arg_strTs: str, arg_boolSalvarPng: bool, arg_boolMostrar: bool, arg_intDpi: int) -> None:
        """
        Gera scatter plot de valores preditos vs reais para regressão.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo
        - arg_arrYReal (array-like): Valores reais (y_true)
        - arg_arrYPred (array-like): Valores preditos (y_pred)
        - arg_strTs (str): Timestamp para nome do arquivo
        - arg_boolSalvarPng (bool): Se True, salva como PNG
        - arg_boolMostrar (bool): Se True, exibe na tela
        - arg_intDpi (int): DPI para salvar PNG
        """
        try:
            if arg_boolSalvarPng and not arg_boolMostrar:
                import matplotlib
                matplotlib.use("Agg")
            
            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            logger.warning(f"Matplotlib indisponível para plotar regressão ({arg_strModelo}): {e}")
            return
        
        try:
            var_arrYReal = np.asarray(arg_arrYReal, dtype=np.float64)
            var_arrYPred = np.asarray(arg_arrYPred, dtype=np.float64)
            
            var_objFig, var_objAxes = plt.subplots(figsize=(8.0, 6.0), dpi=max(72, int(arg_intDpi)))
            
            # Scatter plot: preditos vs reais
            var_objAxes.scatter(var_arrYReal, var_arrYPred, alpha=0.5, s=10, edgecolors='none')
            
            # Linha perfeita (y=x) onde predito seria igual ao real
            var_floatMin = min(var_arrYReal.min(), var_arrYPred.min())
            var_floatMax = max(var_arrYReal.max(), var_arrYPred.max())
            var_objAxes.plot([var_floatMin, var_floatMax], [var_floatMin, var_floatMax], 'r--', lw=2, label='Predição Perfeita')
            
            var_objAxes.set_xlabel('Valores Reais (dias)', fontsize=11)
            var_objAxes.set_ylabel('Valores Preditos (dias)', fontsize=11)
            var_objAxes.set_title(f'Predito vs Real - {arg_strModelo}', fontsize=12, fontweight='bold')
            var_objAxes.legend()
            var_objAxes.grid(True, alpha=0.3)
            
            var_objFig.tight_layout()
            
            if arg_boolSalvarPng:
                var_pathRelatorios = Plots._obter_diretorio_relatorios()
                var_strBaseName = f"regressao_{arg_strModelo}_predito_vs_real_{arg_strTs}"
                
                # Salvar Gráfico PNG
                var_pathPng = var_pathRelatorios / f"{var_strBaseName}.png"
                var_objFig.savefig(var_pathPng, dpi=max(72, int(arg_intDpi)))
                logger.info(f"Plot regressão (predito vs real) salvo: {var_pathPng}")

                # Salvar CSV com os dados da regressão
                var_pathCsv = var_pathRelatorios / f"{var_strBaseName}.csv"
                var_dfRegDados = pd.DataFrame({
                    "Valor_Real": var_arrYReal,
                    "Valor_Predito": var_arrYPred,
                    "Residual": var_arrYReal - var_arrYPred,
                    "Media_Ideal": var_arrYReal  # A linha ideal seria Predito == Real
                })
                var_dfRegDados.to_csv(var_pathCsv, index=False)
                logger.info(f"Dados da regressão (CSV) salvos: {var_pathCsv}")
            
            if arg_boolMostrar:
                plt.show()
        except Exception as e:
            logger.warning(f"Falha ao gerar plot/csv predito vs real ({arg_strModelo}): {e}")
        finally:
            try:
                plt.close("all")
            except Exception:
                pass


    @classmethod
    def _plot_regressao_residuos(cls, arg_strModelo: str, arg_arrYReal, arg_arrYPred, arg_strTs: str, arg_boolSalvarPng: bool, arg_boolMostrar: bool, arg_intDpi: int) -> None:
        """
        Gera scatter plot de resíduos (erros) vs valores preditos.
        Visualiza padrões de erro sistemático no modelo.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo
        - arg_arrYReal (array-like): Valores reais (y_true)
        - arg_arrYPred (array-like): Valores preditos (y_pred)
        - arg_strTs (str): Timestamp para nome do arquivo
        - arg_boolSalvarPng (bool): Se True, salva como PNG
        - arg_boolMostrar (bool): Se True, exibe na tela
        - arg_intDpi (int): DPI para salvar PNG
        """
        try:
            if arg_boolSalvarPng and not arg_boolMostrar:
                import matplotlib
                matplotlib.use("Agg")
            
            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            logger.warning(f"Matplotlib indisponível para plotar resíduos ({arg_strModelo}): {e}")
            return
        
        try:
            var_arrYReal = np.asarray(arg_arrYReal, dtype=np.float64)
            var_arrYPred = np.asarray(arg_arrYPred, dtype=np.float64)
            var_arrResiduos = var_arrYReal - var_arrYPred  # Erro = real - predito
            
            var_objFig, var_objAxes = plt.subplots(figsize=(8.0, 6.0), dpi=max(72, int(arg_intDpi)))
            
            # Scatter plot: resíduos vs preditos
            var_objAxes.scatter(var_arrYPred, var_arrResiduos, alpha=0.5, s=10, edgecolors='none')
            
            # Linha no zero (resíduos perfeitos)
            var_objAxes.axhline(y=0, color='r', linestyle='--', lw=2, label='Sem erro')
            
            var_objAxes.set_xlabel('Valores Preditos (dias)', fontsize=11)
            var_objAxes.set_ylabel('Resíduos = Real - Predito (dias)', fontsize=11)
            var_objAxes.set_title(f'Resíduos vs Predito - {arg_strModelo}', fontsize=12, fontweight='bold')
            var_objAxes.legend()
            var_objAxes.grid(True, alpha=0.3)
            
            var_objFig.tight_layout()
            
            if arg_boolSalvarPng:
                var_pathRelatorios = Plots._obter_diretorio_relatorios()
                var_strBaseName = f"regressao_{arg_strModelo}_residuos_{arg_strTs}"
                var_pathPng = var_pathRelatorios / f"{var_strBaseName}.png"
                var_objFig.savefig(var_pathPng, dpi=max(72, int(arg_intDpi)))
                logger.info(f"Plot regressão (resíduos) salvo: {var_pathPng}")
            
            if arg_boolMostrar:
                plt.show()
        except Exception as e:
            logger.warning(f"Falha ao gerar plot de resíduos ({arg_strModelo}): {e}")
        finally:
            try:
                plt.close("all")
            except Exception:
                pass


