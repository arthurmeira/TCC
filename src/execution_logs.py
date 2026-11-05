"""Importa registros individuais do PostgreSQL e mantém evidências locais."""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import io
import json
import math
import re
import sqlite3
from datetime import datetime, timezone

from pglast import fingerprint
from pglast.parser import ParseError
from src.analyzer import validate_select
from src.config import PROJECT_ROOT

STORE = PROJECT_ROOT / "results" / "logs.sqlite3"
MAX_BYTES = 20 * 1024 * 1024


@contextmanager
def connect():
    STORE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STORE, timeout=20)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS imports (
          id TEXT PRIMARY KEY, source TEXT NOT NULL, imported_at TEXT NOT NULL,
          accepted INTEGER NOT NULL, ignored INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY, import_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
          sql TEXT NOT NULL, duration_ms REAL NOT NULL, occurred_at TEXT,
          database_name TEXT, session_id TEXT);
        CREATE TABLE IF NOT EXISTS experiments (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, report TEXT NOT NULL);
    """)
    try:
        with db:
            yield db
    finally:
        db.close()


def parse_records(content: str, kind: str):
    """CSV/JSON nativos e stderr com duration + statement/execute, incluindo multilinha."""
    content = content.lstrip("\ufeff")
    if kind == "csv":
        rows = list(csv.reader(io.StringIO(content)))
        if rows and "message" in rows[0]:
            yield from csv.DictReader(io.StringIO(content))
        else:
            # Ordem das colunas de csvlog do PostgreSQL 18.
            for row in rows:
                if len(row) >= 14:
                    yield dict(timestamp=row[0], dbname=row[2], session_id=row[5],
                               message=row[13], detail=row[14] if len(row) > 14 else "")
                else:
                    yield {}
    elif kind == "json":
        if content.lstrip().startswith("["):
            data = json.loads(content)
            if not isinstance(data, list):
                raise ValueError("Informe uma lista JSON ou o jsonlog do PostgreSQL.")
            yield from data
        else:
            for line in content.splitlines():
                if line.strip():
                    yield json.loads(line)
    elif kind in {"log", "txt"}:
        # Cada entrada stderr começa com data. Linhas seguintes pertencem ao mesmo SQL.
        for record in re.split(r"(?m)(?=^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", content):
            if record.strip():
                stamp = re.match(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\s+[+-]\d+)?", record)
                yield dict(message=record, timestamp=stamp.group() if stamp else None)
    else:
        raise ValueError("Use um arquivo PostgreSQL .log, .csv, .json ou .jsonl.")


def import_logs(content: str, filename: str, database_name: str | None = None) -> dict:
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("O arquivo deve ter até 20 MB em UTF-8.")
    kind = filename.rsplit(".", 1)[-1].lower()
    if kind == "jsonl":
        kind = "json"
    batch_id = hashlib.sha256(content.encode("utf-8")).hexdigest()
    accepted, ignored, events = 0, 0, []
    with connect() as db:
        previous = db.execute("SELECT * FROM imports WHERE id=?", (batch_id,)).fetchone()
        if previous:
            return {**dict(previous), "duplicate": True}
        for position, record in enumerate(parse_records(content, kind)):
            if position >= 100_000:
                raise ValueError("Divida o arquivo em lotes de até 100 mil registros.")
            if not isinstance(record, dict):
                ignored += 1
                continue
            match = re.search(r"(?:duration|duração):\s*([\d.]+)\s*ms\s+(?:statement:|comando:|execute\s+[^:]+:|executar\s+[^:]+:)\s*(.*)",
                              str(record.get("message", "")), re.S | re.I)
            if not match:
                ignored += 1
                continue
            duration = float(match[1])
            query = match[2].strip()
            try:
                query = validate_select(query)
                shape = fingerprint(query)
                if not math.isfinite(duration) or duration < 0:
                    raise ValueError("Duração inválida")
            except (ValueError, ParseError):
                # Logs de DDL, erros, parâmetros não materializados e SQL incompleto não são reproduzidos.
                ignored += 1
                continue
            source_database = record.get("dbname") or record.get("database_name") or database_name
            # A mesma estrutura em bancos diferentes não representa a mesma população.
            group_id = hashlib.sha256(f"{source_database or 'unknown'}|{shape}".encode()).hexdigest()[:24]
            events.append((f"{batch_id}:{position}", batch_id, group_id, query, duration,
                           record.get("timestamp") or record.get("log_time"),
                           source_database,
                           record.get("session_id")))
            accepted += 1
        if not events:
            raise ValueError("Nenhum SELECT com duração foi encontrado. Use logs com log_min_duration_statement habilitado e valores literais no SQL.")
        archive = STORE.parent / "log_sources"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f"{batch_id}.{kind}").write_bytes(content.encode("utf-8"))
        db.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", events)
        now = datetime.now(timezone.utc).isoformat()
        db.execute("INSERT INTO imports VALUES (?,?,?,?,?)", (batch_id, filename, now, accepted, ignored))
    return dict(id=batch_id, accepted=accepted, ignored=ignored, duplicate=False)


def list_queries() -> dict:
    with connect() as db:
        rows = db.execute("""SELECT fingerprint AS id, COUNT(*) AS calls,
              SUM(duration_ms) AS total_ms, AVG(duration_ms) AS mean_ms,
              MIN(duration_ms) AS min_ms, MAX(duration_ms) AS max_ms,
              COUNT(DISTINCT sql) AS variants, MIN(occurred_at) AS first_seen,
              MAX(occurred_at) AS last_seen, MIN(database_name) AS database_name FROM events GROUP BY fingerprint
              ORDER BY total_ms DESC""").fetchall()
        total = sum(row["total_ms"] for row in rows)
        queries = []
        for row in rows:
            sample = db.execute("SELECT sql, duration_ms FROM events WHERE fingerprint=? ORDER BY duration_ms DESC, id LIMIT 1", (row["id"],)).fetchone()
            queries.append({**dict(row), "sql": sample["sql"], "share": row["total_ms"] / total * 100 if total else 0})
        imports = [dict(row) for row in db.execute("SELECT * FROM imports ORDER BY imported_at DESC")]
    return dict(queries=queries, imports=imports, calls=sum(q["calls"] for q in queries), total_ms=total)


def get_query(query_id: str) -> dict:
    for query in list_queries()["queries"]:
        if query["id"] == query_id:
            return query
    raise ValueError("Consulta não encontrada nos logs importados.")


def save_experiment(report: dict):
    with connect() as db:
        db.execute("INSERT INTO experiments VALUES (?,?,?)", (report["id"], report["created_at"], json.dumps(report, ensure_ascii=False)))


def reports():
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute("SELECT report FROM experiments ORDER BY created_at DESC LIMIT 100")]
