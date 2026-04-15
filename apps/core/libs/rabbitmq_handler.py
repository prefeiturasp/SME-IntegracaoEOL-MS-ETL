"""Handler de logging que publica registros em fila RabbitMQ (→ Logstash → Kibana)."""

import json
import logging
import os
import time
import traceback
from datetime import datetime


class RabbitMQHandler(logging.Handler):
    """Publica registros de log em fila RabbitMQ para ingestão no Kibana via Logstash.

    Campos ETL (execution_id, dominio, job_name, batch_id, etc.) são extraídos
    do LogRecord — injetados previamente pelo ContextualLogger.
    Reconecta automaticamente em caso de falha de conexão com backoff exponencial.
    """

    def __init__(
        self,
        host: str,
        virtual_host: str,
        queue: str,
        username: str,
        password: str,
        max_retries: int = 5,
        retry_delay: int = 1,
    ) -> None:
        super().__init__()
        self.host = host
        self.virtual_host = virtual_host
        self.queue = queue
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self._retry_delay = retry_delay
        self._connection = None
        self._channel = None

    def _establish_connection(self) -> None:
        """Conecta ao RabbitMQ com backoff exponencial entre tentativas."""
        import pika

        delay = self._retry_delay
        for attempt in range(self.max_retries):
            try:
                credentials = pika.PlainCredentials(self.username, self.password)
                params = pika.ConnectionParameters(
                    host=self.host,
                    virtual_host=self.virtual_host,
                    credentials=credentials,
                )
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                self._channel.queue_declare(queue=self.queue, durable=True)
                return
            except Exception:
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2

        raise ConnectionError(
            f"Falha ao conectar ao RabbitMQ em {self.host} após {self.max_retries} tentativas."
        )

    def _build_body(self, record: logging.LogRecord) -> str:
        """Serializa o LogRecord como JSON com campos padrão e contexto ETL."""
        exc_info_str = None
        if record.exc_info:
            exc_info_str = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps({
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "file_name": record.filename,
            "func_name": record.funcName,
            "line_number": record.lineno,
            "module": record.module,
            "process": record.process,
            "thread": record.thread,
            "exc_info": exc_info_str,
            "aplicacao": getattr(record, "aplicacao", os.getenv("NOME_APLICACAO", "SME-IntegracaoEOL-MS-ETL")),
            "ambiente": os.getenv("LOG_ENVIRONMENT", "local"),
            "execution_id": getattr(record, "execution_id", None),
            "dominio": getattr(record, "dominio", None),
            "job_name": getattr(record, "job_name", None),
            "batch_id": getattr(record, "batch_id", None),
            "etapa": getattr(record, "etapa", None),
            "status": getattr(record, "status", None),
            "records_read": getattr(record, "records_read", None),
            "records_written": getattr(record, "records_written", None),
            "entidade": getattr(record, "entidade", None),
            "chave_natural": getattr(record, "chave_natural", None),
            "elasticapm_transaction_id": getattr(record, "elasticapm_transaction_id", None),
            "elasticapm_trace_id": getattr(record, "elasticapm_trace_id", None),
            "elasticapm_span_id": getattr(record, "elasticapm_span_id", None),
            "elasticapm_service_name": getattr(record, "elasticapm_service_name", None),
            "elasticapm_service_environment": getattr(record, "elasticapm_service_environment", None),
        })

    def emit(self, record: logging.LogRecord) -> None:
        """Publica o log na fila RabbitMQ; reconecta automaticamente se necessário."""
        try:
            if self._connection is None or self._connection.is_closed:
                self._establish_connection()
            body = self._build_body(record)
            self._channel.basic_publish(exchange="", routing_key=self.queue, body=body)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Fecha a conexão com o RabbitMQ ao encerrar o handler."""
        if self._connection and not self._connection.is_closed:
            self._connection.close()
        super().close()
