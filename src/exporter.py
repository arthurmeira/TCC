"""Exportação das métricas para CSV e JSON usando a biblioteca padrão."""

import csv
import io
import json
from pathlib import Path
from tempfile import NamedTemporaryFile


FIELDS = (
    "query_id", "query", "calls", "total_exec_time", "mean_exec_time",
    "rows", "impact_score", "collected_at",
)


def write_atomic(path: Path, content: str, encoding: str) -> None:
    """Substitui um arquivo somente depois de terminar sua gravação temporária."""
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding=encoding, newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def export_results(
    metrics: list[dict], output_dir: Path, file_format: str = "both"
) -> list[Path]:
    """Exporta todos os registros da coleta, sem depender do limite dos rankings."""
    if file_format not in ("csv", "json", "both"):
        raise ValueError("Formato de exportação deve ser csv, json ou both.")
    if not metrics:
        raise ValueError("Não há métricas para exportar.")

    records = []
    for metric in sorted(metrics, key=lambda item: (-item["total_exec_time"], item["query_id"])):
        record = {field: metric[field] for field in FIELDS}
        # Identificadores bigint precisam de texto para preservar os dígitos em JSON/JavaScript.
        record["query_id"] = str(record["query_id"])
        records.append(record)

    output_dir = output_dir.resolve()
    documents = []
    if file_format in ("csv", "both"):
        with io.StringIO(newline="") as buffer:
            writer = csv.DictWriter(buffer, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(records)
            documents.append((output_dir / "query_metrics.csv", buffer.getvalue(), "utf-8-sig"))

    if file_format in ("json", "both"):
        content = json.dumps(records, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        documents.append((output_dir / "query_metrics.json", content, "utf-8"))

    # Serializa os formatos solicitados antes de substituir qualquer arquivo existente.
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for path, content, encoding in documents:
        write_atomic(path, content, encoding)
        written_paths.append(path)
    return written_paths
