"""
데이터베이스 서비스 - 요약 내역 저장 (PostgreSQL/SQLite 지원)
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# PostgreSQL 또는 SQLite 사용 여부 결정
USE_POSTGRES = bool(settings.DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("PostgreSQL 데이터베이스 사용 (Supabase)")
else:
    import sqlite3
    logger.info("SQLite 데이터베이스 사용 (로컬)")
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "summaries.db")


def get_connection():
    """데이터베이스 연결 생성"""
    if USE_POSTGRES:
        conn = psycopg2.connect(settings.DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_database():
    """데이터베이스 초기화 - 테이블 생성"""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id SERIAL PRIMARY KEY,
                video_id TEXT NOT NULL UNIQUE,
                video_url TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                duration INTEGER,
                thumbnail_url TEXT,
                notion_url TEXT,
                structured_summary TEXT,
                timeline TEXT,
                processing_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_id ON summaries(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON summaries(created_at)")
    else:
        # SQLite 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL UNIQUE,
                video_url TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                duration INTEGER,
                thumbnail_url TEXT,
                notion_url TEXT,
                structured_summary TEXT,
                timeline TEXT,
                processing_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_id ON summaries(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON summaries(created_at)")

    conn.commit()
    conn.close()

    if USE_POSTGRES:
        logger.info("PostgreSQL 데이터베이스 초기화 완료 (Supabase)")
    else:
        logger.info(f"SQLite 데이터베이스 초기화 완료: {DB_PATH}")


def save_summary(
    video_id: str,
    video_url: str,
    title: str,
    author: str,
    duration: int,
    notion_url: Optional[str],
    structured_summary: Dict,
    timeline: List[Dict],
    processing_time_ms: Optional[int] = None
) -> int:
    """
    요약 결과 저장 (upsert)

    Returns:
        저장된 레코드의 ID
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 썸네일 URL 생성
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    # JSON 직렬화
    summary_json = json.dumps(structured_summary, ensure_ascii=False)
    timeline_json = json.dumps(timeline, ensure_ascii=False)

    try:
        if USE_POSTGRES:
            # PostgreSQL UPSERT
            cursor.execute("""
                INSERT INTO summaries (
                    video_id, video_url, title, author, duration, thumbnail_url,
                    notion_url, structured_summary, timeline, processing_time_ms, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    duration = EXCLUDED.duration,
                    notion_url = EXCLUDED.notion_url,
                    structured_summary = EXCLUDED.structured_summary,
                    timeline = EXCLUDED.timeline,
                    processing_time_ms = EXCLUDED.processing_time_ms,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                video_id, video_url, title, author, duration, thumbnail_url,
                notion_url, summary_json, timeline_json, processing_time_ms
            ))
            record_id = cursor.fetchone()[0]
        else:
            # SQLite UPSERT
            cursor.execute("""
                INSERT INTO summaries (
                    video_id, video_url, title, author, duration, thumbnail_url,
                    notion_url, structured_summary, timeline, processing_time_ms, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    duration = excluded.duration,
                    notion_url = excluded.notion_url,
                    structured_summary = excluded.structured_summary,
                    timeline = excluded.timeline,
                    processing_time_ms = excluded.processing_time_ms,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                video_id, video_url, title, author, duration, thumbnail_url,
                notion_url, summary_json, timeline_json, processing_time_ms
            ))
            record_id = cursor.lastrowid

        conn.commit()
        logger.info(f"요약 저장 완료: {video_id} (ID: {record_id})")
        return record_id

    except Exception as e:
        logger.error(f"요약 저장 실패: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_summary_by_video_id(video_id: str) -> Optional[Dict]:
    """비디오 ID로 요약 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM summaries WHERE video_id = %s", (video_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM summaries WHERE video_id = ?", (video_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return _row_to_dict(row)
    return None


def get_summary_by_id(summary_id: int) -> Optional[Dict]:
    """레코드 ID로 요약 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM summaries WHERE id = %s", (summary_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return _row_to_dict(row)
    return None


def get_recent_summaries(days: int = 30, limit: int = 100) -> List[Dict]:
    """
    최근 N일 내의 요약 목록 조회

    Args:
        days: 조회할 기간 (일)
        limit: 최대 조회 개수

    Returns:
        요약 목록 (간략 정보만)
    """
    conn = get_connection()
    cutoff_date = datetime.now() - timedelta(days=days)

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, video_id, video_url, title, author, duration, thumbnail_url,
                   notion_url, processing_time_ms, created_at
            FROM summaries
            WHERE created_at >= %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (cutoff_date, limit))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, video_id, video_url, title, author, duration, thumbnail_url,
                   notion_url, processing_time_ms, created_at
            FROM summaries
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (cutoff_date.isoformat(), limit))

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_summary_item(row) for row in rows]


def delete_old_summaries(days: int = 30) -> int:
    """
    오래된 요약 삭제

    Args:
        days: 보관 기간 (일)

    Returns:
        삭제된 레코드 수
    """
    conn = get_connection()
    cursor = conn.cursor()
    cutoff_date = datetime.now() - timedelta(days=days)

    if USE_POSTGRES:
        cursor.execute("DELETE FROM summaries WHERE created_at < %s", (cutoff_date,))
    else:
        cursor.execute("DELETE FROM summaries WHERE created_at < ?", (cutoff_date.isoformat(),))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(f"오래된 요약 {deleted_count}개 삭제 완료")
    return deleted_count


def _row_to_dict(row) -> Dict:
    """Row를 전체 딕셔너리로 변환"""
    if USE_POSTGRES:
        # RealDictCursor는 이미 dict 형태
        data = dict(row)
        data["structured_summary"] = json.loads(data["structured_summary"]) if data["structured_summary"] else {}
        data["timeline"] = json.loads(data["timeline"]) if data["timeline"] else []
        # datetime을 문자열로 변환
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat() if hasattr(data["created_at"], 'isoformat') else str(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = data["updated_at"].isoformat() if hasattr(data["updated_at"], 'isoformat') else str(data["updated_at"])
        return data
    else:
        return {
            "id": row["id"],
            "video_id": row["video_id"],
            "video_url": row["video_url"],
            "title": row["title"],
            "author": row["author"],
            "duration": row["duration"],
            "thumbnail_url": row["thumbnail_url"],
            "notion_url": row["notion_url"],
            "structured_summary": json.loads(row["structured_summary"]) if row["structured_summary"] else {},
            "timeline": json.loads(row["timeline"]) if row["timeline"] else [],
            "processing_time_ms": row["processing_time_ms"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


def _row_to_summary_item(row) -> Dict:
    """Row를 목록용 간략 딕셔너리로 변환"""
    if USE_POSTGRES:
        data = dict(row)
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat() if hasattr(data["created_at"], 'isoformat') else str(data["created_at"])
        return data
    else:
        return {
            "id": row["id"],
            "video_id": row["video_id"],
            "video_url": row["video_url"],
            "title": row["title"],
            "author": row["author"],
            "duration": row["duration"],
            "thumbnail_url": row["thumbnail_url"],
            "notion_url": row["notion_url"],
            "processing_time_ms": row["processing_time_ms"],
            "created_at": row["created_at"]
        }


# 모듈 로드 시 데이터베이스 초기화
init_database()
