import logging

from sme_pedagogico_etl.adapters.databases.conexao_eol import healthcheck_eol

logger = logging.getLogger("healthcheck_eol")


def main() -> int:
    try:
        ok = healthcheck_eol()
        if ok:
            print("OK")
            return 0
    except Exception:
        logger.exception("Healthcheck do EOL falhou")
        print("FAIL")
        return 1

    print("FAIL")
    return 1


if __name__ == "__main__":
    logging.basicConfig()
    raise SystemExit(main())