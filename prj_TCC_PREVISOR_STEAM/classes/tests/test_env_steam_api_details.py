"""
Teste para validar leitura das variáveis do .env
"""
import os
from dotenv import load_dotenv

def test_env_steam_api_details():
    load_dotenv()
    batch_size = os.getenv("STEAM_BATCH_SIZE_DETAILS")
    delay = os.getenv("STEAM_DELAY_BETWEEN_BATCHES_DETAILS")
    concurrency = os.getenv("STEAM_ASYNC_CONCURRENCY_DETAILS")
    print("STEAM_BATCH_SIZE_DETAILS =", batch_size)
    print("STEAM_DELAY_BETWEEN_BATCHES_DETAILS =", delay)
    print("STEAM_ASYNC_CONCURRENCY_DETAILS =", concurrency)
    assert batch_size is not None, "STEAM_BATCH_SIZE_DETAILS não foi lida do .env"
    assert delay is not None, "STEAM_DELAY_BETWEEN_BATCHES_DETAILS não foi lida do .env"
    assert concurrency is not None, "STEAM_ASYNC_CONCURRENCY_DETAILS não foi lida do .env"

if __name__ == "__main__":
    test_env_steam_api_details()
