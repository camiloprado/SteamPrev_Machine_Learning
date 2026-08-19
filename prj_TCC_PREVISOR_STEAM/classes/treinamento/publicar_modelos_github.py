"""
Publicação automática de modelos no GitHub Releases.

Lê o manifest.json da pasta de exportação e cria uma GitHub Release com
todos os arquivos .joblib e o manifest como assets.

Uso standalone:
    python -m prj_TCC_PREVISOR_STEAM.classes.treinamento.publicar_modelos_github
    python -m prj_TCC_PREVISOR_STEAM.classes.treinamento.publicar_modelos_github --dry-run
    python -m prj_TCC_PREVISOR_STEAM.classes.treinamento.publicar_modelos_github --force

Variáveis de ambiente obrigatórias:
    GITHUB_TOKEN   → Personal Access Token com permissão 'repo' (contents:write)

Variáveis de ambiente opcionais:
    GITHUB_REPO    → Repositório no formato 'owner/repo' (padrão: lido do manifest.json)
"""

import requests
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

logger = logging.getLogger("treino.publicar_github")

# ── Constantes ────────────────────────────────────────────────────────────────

CON_STR_GITHUB_API_BASE = "https://api.github.com"
CON_PATH_EXPORT_DEFAULT = (
    Path(__file__).resolve().parents[2] / "resources" / "models" / "export"
)

# Extensões de arquivo que serão enviadas como assets da Release
CON_SET_EXTENSOES_ASSET = {".joblib", ".json"}

# Timeout para uploads (modelos grandes podem demorar)
CON_INT_TIMEOUT_UPLOAD = 600  # 10 minutos

# Máximo de tentativas por arquivo
CON_INT_MAX_TENTATIVAS = 3


# ── Helpers HTTP ──────────────────────────────────────────────────────────────

def _get_session(arg_strToken: str):
    """
    Cria uma sessão requests com headers de autenticação GitHub.
    
    - Parâmetros:
        - arg_strToken (str): Token de autenticação GitHub.
    
    - Retorna:
        - requests.Session: Sessão requests com headers de autenticação GitHub.
    """
    var_objSession = requests.Session()
    var_objSession.headers.update({
        "Authorization": f"Bearer {arg_strToken}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return var_objSession


def _calcular_sha256(arg_pathArquivo: Path) -> str:
    """
    Calcula SHA-256 de um arquivo local.
    
    - Parâmetros:
        - arg_pathArquivo (Path): Caminho do arquivo.
    
    - Retorna:
        - str: Hash SHA-256 do arquivo.
    """
    var_objHash = hashlib.sha256()
    with open(arg_pathArquivo, "rb") as var_f:
        for var_chunk in iter(lambda: var_f.read(65536), b""):
            var_objHash.update(var_chunk)
    return var_objHash.hexdigest()


def _formatar_tamanho(arg_intBytes: int) -> str:
    """
    Formata tamanho em bytes para string legível.
    
    - Parâmetros:
        - arg_intBytes (int): Tamanho em bytes.
    
    - Retorna:
        - str: Tamanho formatado.
    """
    if arg_intBytes >= 1024 ** 3:
        return f"{arg_intBytes / (1024 ** 3):.1f} GB"
    if arg_intBytes >= 1024 ** 2:
        return f"{arg_intBytes / (1024 ** 2):.1f} MB"
    return f"{arg_intBytes / 1024:.1f} KB"


# ── Lógica GitHub ─────────────────────────────────────────────────────────────

def _obter_release_existente(arg_objSession, arg_strRepo: str, arg_strTag: str) -> dict | None:
    """
    Verifica se já existe uma release com a tag informada.
    
    - Parâmetros:
        - arg_objSession: Sessão requests com headers de autenticação GitHub.
        - arg_strRepo: Repositório no formato 'owner/repo'.
        - arg_strTag: Tag da release.
    
    - Retorna:
        - dict com dados da release ou None se não existir.
    """
    var_strUrl = f"{CON_STR_GITHUB_API_BASE}/repos/{arg_strRepo}/releases/tags/{arg_strTag}"
    var_objResp = arg_objSession.get(var_strUrl, timeout=30)
    if var_objResp.status_code == 200:
        return var_objResp.json()
    return None


def _criar_release(arg_objSession, arg_strRepo: str, arg_strTag: str, arg_strNome: str, arg_strBody: str) -> dict:
    """
    Cria uma nova GitHub Release.
    
    - Parâmetros:
        - arg_objSession: Sessão requests com headers de autenticação GitHub.
        - arg_strRepo: Repositório no formato 'owner/repo'.
        - arg_strTag: Tag da release.
        - arg_strNome: Nome da release.
        - arg_strBody: Descrição da release.
    
    - Retorna:
        - dict com dados da release criada.
    """
    var_strUrl = f"{CON_STR_GITHUB_API_BASE}/repos/{arg_strRepo}/releases"
    var_dictPayload = {
        "tag_name": arg_strTag,
        "name": arg_strNome,
        "body": arg_strBody,
        "draft": False,
        "prerelease": False,
    }
    var_objResp = arg_objSession.post(var_strUrl, json=var_dictPayload, timeout=30)
    var_objResp.raise_for_status()
    var_dictRelease = var_objResp.json()
    logger.info(f" Release criada: {var_dictRelease['html_url']}")
    return var_dictRelease


def _atualizar_release(arg_objSession, arg_strRepo: str, arg_intReleaseId: int, arg_strNome: str, arg_strBody: str) -> dict:
    """
    Atualiza o nome e body de uma release existente.
    
    - Parâmetros:
        - arg_objSession: Sessão requests com headers de autenticação GitHub.
        - arg_strRepo: Repositório no formato 'owner/repo'.
        - arg_intReleaseId: ID da release.
        - arg_strNome: Nome da release.
        - arg_strBody: Descrição da release.
    
    - Retorna:
        - dict com dados da release atualizada.
    """
    var_strUrl = f"{CON_STR_GITHUB_API_BASE}/repos/{arg_strRepo}/releases/{arg_intReleaseId}"
    var_objResp = arg_objSession.patch(
        var_strUrl,
        json={"name": arg_strNome, "body": arg_strBody},
        timeout=30,
    )
    var_objResp.raise_for_status()
    logger.info(f" Release atualizada: {var_objResp.json()['html_url']}")
    return var_objResp.json()


def _remover_asset_existente(arg_objSession, arg_strRepo: str, arg_intAssetId: int, arg_strNome: str) -> None:
    """
    Remove um asset já existente na release (necessário antes de re-upload).
    
    - Parâmetros:
        - arg_objSession: Sessão requests com headers de autenticação GitHub.
        - arg_strRepo: Repositório no formato 'owner/repo'.
        - arg_intAssetId: ID da release.
        - arg_strNome: Nome do asset.
    
    - Retorna:
        - None
    """
    var_strUrl = f"{CON_STR_GITHUB_API_BASE}/repos/{arg_strRepo}/releases/assets/{arg_intAssetId}"
    arg_objSession.delete(var_strUrl, timeout=30)
    logger.debug(f"  Asset removido: {arg_strNome}")


def _upload_asset(arg_objSession, arg_strUploadUrl: str, arg_pathArquivo: Path, arg_intTentativa: int = 1) -> bool:
    """
    Faz upload de um arquivo como asset de uma GitHub Release.
    
    - Parâmetros:
        - arg_objSession: Sessão requests com headers de autenticação GitHub.
        - arg_strUploadUrl: URL de upload da release.
        - arg_pathArquivo: Caminho do arquivo a ser enviado.
        - arg_intTentativa: Número da tentativa atual (padrão: 1).
    
    - Retorna:
        - bool: True se upload bem-sucedido.
    """
    var_strUrl = arg_strUploadUrl.split("{")[0]
    var_intTamanho = arg_pathArquivo.stat().st_size

    logger.info(
        f"  [{arg_intTentativa}/{CON_INT_MAX_TENTATIVAS}] "
        f"{arg_pathArquivo.name} ({_formatar_tamanho(var_intTamanho)})..."
    )

    var_intInicio = time.time()
    try:
        with open(arg_pathArquivo, "rb") as var_f:
            var_objResp = arg_objSession.post(
                var_strUrl,
                params={"name": arg_pathArquivo.name},
                data=var_f,
                headers={"Content-Type": "application/octet-stream"},
                timeout=CON_INT_TIMEOUT_UPLOAD,
            )

        var_floatDuracao = time.time() - var_intInicio
        var_floatVelocidade = var_intTamanho / (1024 * 1024 * max(var_floatDuracao, 0.1))

        if var_objResp.status_code in (200, 201):
            logger.info(
                f"   {arg_pathArquivo.name} enviado "
                f"({var_floatDuracao:.1f}s, {var_floatVelocidade:.1f} MB/s)"
            )
            return True

        logger.warning(
            f"    Upload de {arg_pathArquivo.name} retornou "
            f"status {var_objResp.status_code}: {var_objResp.text[:200]}"
        )
        return False

    except Exception as e:
        logger.error(f"   Erro no upload de {arg_pathArquivo.name}: {e}")
        return False


# ── Função Principal ──────────────────────────────────────────────────────────

def publicar_modelos(arg_pathExport: Path | None = None, arg_strRepo: str | None = None, arg_strTag: str | None = None, arg_boolDryRun: bool = False, arg_boolForce: bool = False) -> bool:
    """
    Publica os modelos exportados como uma GitHub Release.

    Fluxo:
    1. Lê o manifest.json da pasta de exportação
    2. Cria ou atualiza a release com a tag da versão
    3. Faz upload de todos os .joblib e manifest.json como assets
    4. Retorna True se publicação 100% bem-sucedida

    Parâmetros:
    - arg_pathExport (Path | None): Pasta de exportação. Padrão: resources/models/export
    - arg_strRepo (str | None): Repositório 'owner/repo'. Padrão: env GITHUB_REPO ou manifest.
    - arg_strTag (str | None): Tag da release. Padrão: 'models-v{versao}'
    - arg_boolDryRun (bool): Apenas simula sem fazer upload.
    - arg_boolForce (bool): Re-faz upload mesmo que assets já existam.

    Retorna:
    - bool: True se publicação concluída sem erros.
    """
    # ── Validar token ──
    var_strToken = os.getenv("GITHUB_TOKEN", "")
    if not var_strToken and not arg_boolDryRun:
        logger.error(
            " GITHUB_TOKEN não configurado.\n"
            "   Crie um Personal Access Token em https://github.com/settings/tokens\n"
            "   com permissão 'Contents: Read and write' e adicione ao .env:\n"
            "   GITHUB_TOKEN=ghp_..."
        )
        return False

    # ── Pasta de exportação ──
    var_pathExport = arg_pathExport or CON_PATH_EXPORT_DEFAULT
    var_pathManifest = var_pathExport / "manifest.json"

    if not var_pathManifest.exists():
        logger.error(f" manifest.json não encontrado em: {var_pathExport}")
        return False

    # ── Ler manifest ──
    with open(var_pathManifest, "r", encoding="utf-8") as var_f:
        var_dictManifest = json.load(var_f)

    var_strVersao = var_dictManifest.get("version", "0.0")
    var_strExportadoEm = var_dictManifest.get("exported_at", "")[:10]

    # ── Repositório ──
    var_strRepo = (
        arg_strRepo
        or os.getenv("GITHUB_REPO", "")
        or var_dictManifest.get("github_repo", "")
    )
    if not var_strRepo:
        logger.error(
            " Repositório GitHub não configurado.\n"
            "   Defina GITHUB_REPO=owner/repo no .env ou no campo 'github_repo' do manifest.json."
        )
        return False

    # ── Tag e nome da release ──
    var_strTag = arg_strTag or f"models-v{var_strVersao}"
    var_strNomeRelease = f"Modelos ML v{var_strVersao} ({var_strExportadoEm})"

    # ── Body com métricas ──
    var_listLinhasBody = [
        f"## Modelos ML — Previsor Steam v{var_strVersao}",
        f"",
        f"**Exportado em:** `{var_strExportadoEm}`  ",
        f"**Repositório de treinamento:** `camiloprado/Projeto_TCC_CC`",
        f"",
        f"### Métricas dos Modelos",
        f"| Arquivo | Algoritmo | Horizonte | Métrica |",
        f"|---------|-----------|-----------|---------|",
    ]
    for var_strArquivo, var_dictInfo in var_dictManifest.get("models", {}).items():
        var_strAlgo = var_dictInfo.get("algorithm", "N/A")
        var_strHorizonte = var_dictInfo.get("horizon", "N/A")
        var_dictMetricas = var_dictInfo.get("metrics", {})
        if "f1_macro" in var_dictMetricas:
            var_strMetrica = f"F1={var_dictMetricas['f1_macro']:.4f}"
        elif "rmse" in var_dictMetricas:
            var_strMetrica = f"RMSE={var_dictMetricas['rmse']:.4f}"
        else:
            var_strMetrica = "N/A"
        var_listLinhasBody.append(
            f"| `{var_strArquivo}` | {var_strAlgo} | {var_strHorizonte} | {var_strMetrica} |"
        )
    var_listLinhasBody.extend([
        f"",
        f"### Download automático",
        f"A extensão baixa os modelos automaticamente via `scripts/download_models.py`.",
        f"",
        f"```bash",
        f"# Download manual",
        f"python -m scripts.download_models --force",
        f"```",
    ])
    var_strBody = "\n".join(var_listLinhasBody)

    # ── Listar arquivos ──
    var_listArquivos = sorted([
        var_pathCaminho for var_pathCaminho in var_pathExport.iterdir()
        if var_pathCaminho.suffix in CON_SET_EXTENSOES_ASSET and var_pathCaminho.is_file()
    ])

    if not var_listArquivos:
        logger.error(f" Nenhum .joblib ou .json encontrado em {var_pathExport}")
        return False

    var_intTotalBytes = sum(var_pathCaminho.stat().st_size for var_pathCaminho in var_listArquivos)

    # ── Log resumo ──
    logger.info("=" * 60)
    logger.info("PUBLICAÇÃO AUTOMÁTICA — GITHUB RELEASES")
    logger.info("=" * 60)
    logger.info(f"Repositório : {var_strRepo}")
    logger.info(f"Tag         : {var_strTag}")
    logger.info(f"Release     : {var_strNomeRelease}")
    logger.info(f"Arquivos    : {len(var_listArquivos)} ({_formatar_tamanho(var_intTotalBytes)})")
    logger.info(f"Dry-run     : {'Sim — nenhum upload será feito' if arg_boolDryRun else 'Não'}")
    logger.info("-" * 60)
    for var_pathArq in var_listArquivos:
        logger.info(f"  {var_pathArq.name} ({_formatar_tamanho(var_pathArq.stat().st_size)})")
    logger.info("=" * 60)

    if arg_boolDryRun:
        logger.info(" Dry-run concluído. Nenhum arquivo foi enviado.")
        return True

    # ── Criar/Atualizar release ──
    var_objSession = _get_session(var_strToken)

    var_dictReleaseExistente = _obter_release_existente(var_objSession, var_strRepo, var_strTag)
    if var_dictReleaseExistente:
        logger.info(f" Release '{var_strTag}' já existe. Atualizando metadados...")
        var_dictRelease = _atualizar_release(
            var_objSession,
            var_strRepo,
            var_dictReleaseExistente["id"],
            var_strNomeRelease,
            var_strBody,
        )
        var_dictAssetsExistentes = {
            var_dictAsset["name"]: var_dictAsset["id"]
            for var_dictAsset in var_dictReleaseExistente.get("assets", [])
        }
    else:
        logger.info(f" Criando release '{var_strTag}'...")
        var_dictRelease = _criar_release(
            var_objSession, var_strRepo, var_strTag, var_strNomeRelease, var_strBody
        )
        var_dictAssetsExistentes = {}

    var_strUploadUrl = var_dictRelease["upload_url"]

    # ── Upload assets ──
    logger.info(f"\n Iniciando upload de {len(var_listArquivos)} arquivos...")
    var_intSucesso = 0
    var_intFalha = 0

    for var_pathArquivo in var_listArquivos:
        var_strNomeArquivo = var_pathArquivo.name

        # Pula se já existe e não está forçando
        if var_strNomeArquivo in var_dictAssetsExistentes and not arg_boolForce:
            logger.info(f"   {var_strNomeArquivo} — já existe (use --force para re-upload)")
            var_intSucesso += 1
            continue

        # Remove asset existente antes de re-upload
        if var_strNomeArquivo in var_dictAssetsExistentes:
            _remover_asset_existente(
                var_objSession,
                var_strRepo,
                var_dictAssetsExistentes[var_strNomeArquivo],
                var_strNomeArquivo,
            )

        # Upload com retentativas
        var_boolOk = False
        for var_intTentativa in range(1, CON_INT_MAX_TENTATIVAS + 1):
            var_boolOk = _upload_asset(
                var_objSession,
                var_strUploadUrl,
                var_pathArquivo,
                var_intTentativa,
            )
            if var_boolOk:
                break
            if var_intTentativa < CON_INT_MAX_TENTATIVAS:
                logger.info("   Aguardando 5s antes de nova tentativa...")
                time.sleep(5)

        if var_boolOk:
            var_intSucesso += 1
        else:
            var_intFalha += 1
            logger.error(f"  Falha definitiva no upload de {var_strNomeArquivo}")

    # ── Resultado ──
    logger.info("=" * 60)
    if var_intFalha == 0:
        logger.info(f" PUBLICAÇÃO CONCLUÍDA — {var_intSucesso} assets enviados com sucesso.")
        logger.info(f"   Release: {var_dictRelease['html_url']}")
        return True
    else:
        logger.warning(
            f" PUBLICAÇÃO PARCIAL — {var_intSucesso} enviados, {var_intFalha} com falha."
        )
        logger.info(f"   Release: {var_dictRelease['html_url']}")
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    load_dotenv()  # Carrega as variáveis do .env local para testes standalone

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    var_objParser = argparse.ArgumentParser(
        description="Publica modelos ML treinados como GitHub Release"
    )
    var_objParser.add_argument(
        "--export-dir", type=str, default=None,
        help="Pasta de exportação. Padrão: resources/models/export"
    )
    var_objParser.add_argument(
        "--repo", type=str, default=None,
        help="Repositório 'owner/repo'. Padrão: env GITHUB_REPO ou manifest.json"
    )
    var_objParser.add_argument(
        "--tag", type=str, default=None,
        help="Tag da release. Padrão: 'models-v{versão}'"
    )
    var_objParser.add_argument(
        "--dry-run", action="store_true",
        help="Apenas simula sem fazer upload"
    )
    var_objParser.add_argument(
        "--force", action="store_true",
        help="Re-faz upload mesmo que os assets já existam"
    )

    var_objArgs = var_objParser.parse_args()

    var_boolOk = publicar_modelos(
        arg_pathExport=Path(var_objArgs.export_dir) if var_objArgs.export_dir else None,
        arg_strRepo=var_objArgs.repo,
        arg_strTag=var_objArgs.tag,
        arg_boolDryRun=var_objArgs.dry_run,
        arg_boolForce=var_objArgs.force,
    )
    sys.exit(0 if var_boolOk else 1)
