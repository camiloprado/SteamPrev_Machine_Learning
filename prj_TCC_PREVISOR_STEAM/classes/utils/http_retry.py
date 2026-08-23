"""
Utilitários compartilhados de retry/backoff para clientes HTTP assíncronos.

Extraído de steam_api.py e itad_api.py, onde a mesma lógica de retry com
backoff exponencial para erros 429 (Too Many Requests) e 502 (Bad Gateway)
estava duplicada quase que integralmente entre os dois clientes.

O valor de backoff base é recebido como PARÂMETRO da função (e não lido de um
atributo de classe mutável, como era antes em `cls._var_intRetryBackoffBase`),
para que chamadas concorrentes (ex.: `asyncio.gather` disparando
`fetch_details_bulk_batched` e `fetch_reviews_summary_batched` ao mesmo tempo)
não sobrescrevam a configuração uma da outra, o que tornava o backoff
não determinístico.

Também foi adicionado jitter aleatório ao cálculo do tempo de espera, para
evitar que múltiplas chamadas concorrentes acordem exatamente no mesmo
instante e martelem a API novamente ao mesmo tempo (thundering herd).
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import asyncio
import logging
import random

import aiohttp

CON_DEFAULT_MAX_RETRIES = 3


def parse_retry_after_seconds(arg_resp: aiohttp.ClientResponse) -> int | None:
    """
    Extrai o tempo de espera (em segundos) do header 'Retry-After' de uma resposta HTTP.
    Suporta tanto o formato numérico (segundos) quanto o formato de data HTTP (RFC 2822).

    Parâmetros:
    - arg_resp (aiohttp.ClientResponse): Resposta HTTP recebida.

    Retorna:
    - int | None: Segundos a esperar (mínimo 1), ou None se o header estiver ausente/inválido.
    """
    var_strRetryAfter = arg_resp.headers.get("Retry-After")
    if not var_strRetryAfter:
        return None

    var_strRetryAfter = var_strRetryAfter.strip()

    try:
        var_floatSeconds = float(var_strRetryAfter)
        if var_floatSeconds < 0:
            return None
        return max(1, int(var_floatSeconds))
    except ValueError:
        pass

    try:
        var_dateRetryAt = parsedate_to_datetime(var_strRetryAfter)
        if var_dateRetryAt.tzinfo is None:
            var_dateRetryAt = var_dateRetryAt.replace(tzinfo=timezone.utc)
        var_dateNow = datetime.now(timezone.utc)
        var_intSeconds = int((var_dateRetryAt - var_dateNow).total_seconds())
        return max(1, var_intSeconds)
    except Exception:
        return None


async def retry_with_backoff(
    arg_clientSession: aiohttp.ClientSession,
    arg_strUrl: str,
    arg_intRetryBackoffBase: int,
    arg_anyId: int | str,
    arg_objLogger: logging.Logger,
    arg_strTipo: str = "",
    arg_strLogPrefix: str = "",
    arg_dictParams: dict | None = None,
    arg_intMaxRetries: int = CON_DEFAULT_MAX_RETRIES,
) -> dict | list | None:
    """
    Retry com backoff exponencial + jitter para erros 429 (Too Many Requests) e 502 (Bad Gateway).

    Compartilhado entre o cliente Steam (steam_api.py) e o cliente ITAD (itad_api.py).

    Parâmetros:
    - arg_clientSession (aiohttp.ClientSession): Sessão HTTP reutilizável.
    - arg_strUrl (str): URL completa (ou já formatada com o path do recurso) para a requisição.
    - arg_intRetryBackoffBase (int): Base (em segundos) usada no cálculo do backoff exponencial.
                                      Recebida explicitamente como parâmetro (não é estado de classe)
                                      para ser segura em chamadas concorrentes.
    - arg_anyId (int | str): Identificador do recurso sendo buscado (AppID ou ITAD Plain), usado nos logs.
    - arg_objLogger (logging.Logger): Logger a ser usado para as mensagens de retry.
    - arg_strTipo (str): Tipo de dados sendo buscado (ex.: 'detalhes', 'reviews', 'lookup_ids', 'preco'), para logs mais claros.
    - arg_strLogPrefix (str): Prefixo usado nas mensagens de log (ex.: 'STEAM', 'ITAD').
    - arg_dictParams (dict | None): Parâmetros de query string da requisição (opcional).
    - arg_intMaxRetries (int): Número máximo de tentativas. (Padrão: 3)

    Retorna:
    - dict | list | None: Dados retornados pela API (JSON decodificado) ou None se falhar.
    """
    for var_intAttempt in range(arg_intMaxRetries):
        try:
            async with arg_clientSession.get(arg_strUrl, params=arg_dictParams) as resp:
                if resp.status == 429:
                    var_fltWaitTime = parse_retry_after_seconds(resp)
                    if var_fltWaitTime is None:
                        var_fltWaitTime = (2 ** var_intAttempt) * arg_intRetryBackoffBase + random.uniform(0, arg_intRetryBackoffBase)
                    arg_objLogger.warning(
                        f"{arg_strLogPrefix} retry ({arg_strTipo}) id={arg_anyId} status=429 "
                        f"tentativa={var_intAttempt+1}/{arg_intMaxRetries} espera={var_fltWaitTime:.1f}s"
                    )
                    await asyncio.sleep(var_fltWaitTime)
                    continue
                if resp.status == 502:
                    var_fltWaitTime = (2 ** var_intAttempt) * arg_intRetryBackoffBase + random.uniform(0, arg_intRetryBackoffBase)
                    arg_objLogger.warning(
                        f"{arg_strLogPrefix} retry ({arg_strTipo}) id={arg_anyId} status=502 "
                        f"tentativa={var_intAttempt+1}/{arg_intMaxRetries} espera={var_fltWaitTime:.1f}s"
                    )
                    await asyncio.sleep(var_fltWaitTime)
                    continue
                elif resp.status == 200:
                    return await resp.json()
                else:
                    arg_objLogger.debug(
                        f"{arg_strLogPrefix} resposta id={arg_anyId} status={resp.status} tentativa={var_intAttempt+1}"
                    )
                    return None
        except Exception as e:
            if var_intAttempt == arg_intMaxRetries - 1:
                arg_objLogger.error(f"{arg_strLogPrefix} id={arg_anyId}: Falha após {arg_intMaxRetries} tentativas - {e}")
                return None
            await asyncio.sleep(5)  # Espera 5s entre tentativas com erro
    return None
