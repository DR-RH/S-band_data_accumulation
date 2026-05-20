from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .normalize import normalize_log_text
from .extract import extract_timestamp_segments
from .inject import inject_timestamp_into_faf320

# ロガーの設定（アプリケーション全体の設定に従うのが望ましい）
logger = logging.getLogger(__name__)
DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[2] / "output" / "reports.jsonl"
SYNC_WORD = bytes.fromhex("FAF320")

class DataIntegrityError(ValueError):
    """データの整合性に問題がある場合に発生させる例外"""
    pass

def validate_hex_string(hex_str: str) -> None:
    """
    16進数文字列として妥当か検証する
    """
    if not re.fullmatch(r"^[0-9A-Fa-f]*$", hex_str):
        raise DataIntegrityError("Hex string contains invalid characters.")
    
def hex_string_to_bytes(hex_str: str) -> bytes:
    validate_hex_string(hex_str)

    if len(hex_str) % 2 != 0:
        raise DataIntegrityError(
            f"Odd length hex string (len={len(hex_str)})"
        )

    try:
        return bytes.fromhex(hex_str)
    except ValueError as e:
        raise DataIntegrityError(f"Conversion failed: {e}") from e


def append_jsonl_report(report_path: Path | None, report: dict) -> None:
    if report_path is None:
        return

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        logger.warning("Failed to write report to %s", report_path, exc_info=True)


def safe_filename_part(value: str | None) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("._")
    return safe or "unknown"


def report_artifact_path(
    report_path: Path | None,
    report_type: str,
    *,
    source_path: Path | None = None,
    artifact_name: str | None = None,
    created_at: datetime,
) -> Path | None:
    if report_path is None:
        return None

    suffix = source_path.suffix if source_path is not None and source_path.suffix else ".txt"
    stem = safe_filename_part(artifact_name or (source_path.stem if source_path is not None else None))
    timestamp = created_at.strftime("%Y%m%dT%H%M%S%fZ")
    return report_path.parent / "report_artifacts" / report_type / f"{stem}_{timestamp}{suffix}"


def copy_report_artifact(
    copy_path: Path | None,
    *,
    source_path: Path | None = None,
    raw_log_text: str | None = None,
) -> Path | None:
    if copy_path is None:
        return None

    try:
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path is not None and source_path.exists():
            shutil.copy2(source_path, copy_path)
        elif raw_log_text is not None:
            copy_path.write_text(raw_log_text, encoding="utf-8")
        else:
            return None
    except OSError:
        logger.warning("Failed to copy report artifact to %s", copy_path, exc_info=True)
        return None

    return copy_path


def report_relative_path(path: Path | None, report_path: Path | None) -> str | None:
    if path is None:
        return None

    if report_path is not None:
        try:
            return str(path.relative_to(report_path.parent.parent))
        except ValueError:
            pass
    return str(path)


def odd_hex_recovery_candidates(hex_stream: str) -> list[dict]:
    return [
        {
            "action": "append_trailing_zero",
            "hex_stream": f"{hex_stream}0",
            "detail": {"appended": "0"},
        },
        {
            "action": "prepend_leading_zero",
            "hex_stream": f"0{hex_stream}",
            "detail": {"prepended": "0"},
        },
        {
            "action": "drop_first_nibble",
            "hex_stream": hex_stream[1:],
            "detail": {"dropped": "first_nibble"},
        },
        {
            "action": "drop_trailing_nibble",
            "hex_stream": hex_stream[:-1],
            "detail": {"dropped": "trailing_nibble"},
        },
    ]


def score_sync_words(hex_stream: str) -> int:
    return bytes.fromhex(hex_stream).count(SYNC_WORD)


def choose_odd_hex_recovery(hex_stream: str) -> tuple[str, dict, list[dict]]:
    best_candidate = None
    best_score = -1
    scored_candidates = []

    for candidate in odd_hex_recovery_candidates(hex_stream):
        sync_count = score_sync_words(candidate["hex_stream"])
        score = {
            "action": candidate["action"],
            "hex_length": len(candidate["hex_stream"]),
            "sync_count": sync_count,
        }
        scored_candidates.append(score)

        if sync_count > best_score:
            best_candidate = candidate
            best_score = sync_count

    return best_candidate["hex_stream"], {**best_candidate["detail"], "action": best_candidate["action"]}, scored_candidates


def recover_odd_hex_stream(
    hex_stream: str,
    *,
    source_path: Path | None = None,
    artifact_name: str | None = None,
    report_path: Path | None = None,
    raw_log_text: str | None = None,
) -> str:
    if len(hex_stream) % 2 == 0:
        return hex_stream

    original_length = len(hex_stream)
    recovered, selected, candidates = choose_odd_hex_recovery(hex_stream)
    created_at = datetime.now(timezone.utc)
    copy_path = copy_report_artifact(
        report_artifact_path(
            report_path,
            "odd_hex_recovery",
            source_path=source_path,
            artifact_name=artifact_name,
            created_at=created_at,
        ),
        source_path=source_path,
        raw_log_text=raw_log_text,
    )
    report = {
        "type": "odd_hex_recovery",
        "level": "warning",
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "stage": "ingest_raw_log",
        "input_file": str(source_path) if source_path is not None else None,
        "artifact_name": artifact_name,
        "artifact_copy": report_relative_path(copy_path, report_path),
        "action": selected["action"],
        "original_hex_length": original_length,
        "recovered_hex_length": len(recovered),
        "selected_sync_count": max(candidate["sync_count"] for candidate in candidates),
        "recovery_candidates": candidates,
        "crc_check_follows": True,
    }
    report.update({key: value for key, value in selected.items() if key != "action"})

    logger.warning(
        "Odd length hex stream recovered by %s: %s -> %s, sync_count=%s",
        selected["action"],
        original_length,
        len(recovered),
        report["selected_sync_count"],
    )
    append_jsonl_report(report_path, report)
    return recovered

def build_timestamp_injected_binary(
    raw_log_text: str,
    timestamp_pattern: re.Pattern,
    source_path: Path | None = None,
    artifact_name: str | None = None,
    report_path: Path | None = DEFAULT_REPORT_PATH,
    ) -> bytes:
    """
    Full step1 transformation:
    raw log text -> timestamp injected binary
    """
    
    try:
        normalized = normalize_log_text(raw_log_text)

        segments = extract_timestamp_segments(
            normalized,
            timestamp_pattern,
        )
        
        if not segments:
            logger.warning("No timestamp segments extracted. Output will be empty.")

        injected_segments = []
        for i, (ts, segment) in enumerate(segments):
            # 個別のセグメントに対しても検証を行うことが推奨される
            # ここで異常があれば、どのタイムスタンプ付近のデータか特定できる
            try:
                validate_hex_string(segment)
                injected = inject_timestamp_into_faf320(segment, ts)
                injected_segments.append(injected)
            except DataIntegrityError as e:
                raise DataIntegrityError(
                    f"Invalid characters found in segment {i} (Timestamp: {ts})"
                ) from e
            

        hex_stream = "".join(injected_segments)
        hex_stream = recover_odd_hex_stream(
            hex_stream,
            source_path=source_path,
            artifact_name=artifact_name,
            report_path=report_path,
            raw_log_text=raw_log_text,
        )
        try:
            data = hex_string_to_bytes(hex_stream)
        except DataIntegrityError as e:
            logger.error(f"hex conversion failed: {e}")
            raise

        return data
        
    except Exception as e:
        logger.exception("Failed to build binary stream.")
        raise
