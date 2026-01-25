import os
from typing import Optional

from ormWP import Wpcontent, Waterpoint

import psycopg2
from psycopg2.extras import Json

from openai import AzureOpenAI

from bson import ObjectId
from datetime import datetime, date


def env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


PG_HOST = env("PG_HOST", "127.0.0.1")
PG_PORT = int(env("PG_PORT", "5555"))
PG_DB = env("PG_DB", "vectordb")
PG_USER = env("PG_USER", "pguser")
PG_PASSWORD = env("PG_PASSWORD")

AZURE_OPENAI_ENDPOINT = env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = env("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")


def get_pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)


def get_embedding_from_foundry(text: str):
    resp = client.embeddings.create(
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        input=text,
    )
    return resp.data[0].embedding


def clean_for_json(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    return obj


def build_text_for_embedding(wp: Wpcontent) -> Optional[str]:
    wp_name = None
    wp_ref = getattr(wp, "waterpoint", None)
    wp_doc = None

    if wp_ref is not None:
        if isinstance(wp_ref, Waterpoint):
            wp_doc = wp_ref
        elif hasattr(wp_ref, "id"):
            try:
                wp_doc = Waterpoint.objects(id=wp_ref.id).first()
            except Exception:
                wp_doc = None
        else:
            try:
                wp_doc = Waterpoint.objects(id=wp_ref).first()
            except Exception:
                wp_doc = None

    if wp_doc is not None and hasattr(wp_doc, "name"):
        wp_name = str(wp_doc.name)

    content_dict = getattr(wp, "content", {}) or {}
    values = content_dict.get("values", []) or []

    parts = []

    if wp_name:
        parts.append(f"waterpoint {wp_name}")

    for item in values:
        if isinstance(item, dict):
            if "content" in item:
                parts.append(str(item["content"]))
            else:
                if item:
                    first_val = next(iter(item.values()))
                    parts.append(str(first_val))

    final_text = " ".join(parts).strip()
    return final_text or None


def main():
    try:
        conn = get_pg_conn()
        conn.close()
        print("Connected to Postgres")
    except Exception as e:
        print("Postgres connection error:", e)
        raise

    texts_qs = Wpcontent.objects(__raw__={"content.type": "text"})
    total_docs = texts_qs.count()
    print(f"Total documents to process: {total_docs}")

    pg_conn = get_pg_conn()
    pg_cur = pg_conn.cursor()

    count = 0

    for wp in texts_qs:
        mongo_id = str(wp.id)

        text = build_text_for_embedding(wp)
        if not text:
            continue

        embedding = get_embedding_from_foundry(text)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        raw_metadata = wp.to_mongo().to_dict()
        metadata = clean_for_json(raw_metadata)

        pg_cur.execute(
            """
            INSERT INTO documents (mongo_id, content, metadata, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            (mongo_id, text, Json(metadata), embedding_str),
        )

        count += 1
        if count % 20 == 0:
            pg_conn.commit()
            print(f"{count} / {total_docs} inserted")

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()

    print(f"Import complete: {count} inserted")


if __name__ == "__main__":
    main()