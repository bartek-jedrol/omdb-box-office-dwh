import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

import requests
from dotenv import load_dotenv
from google.cloud import bigquery, storage  # type: ignore[attr-defined]

load_dotenv()

OMDB_URL = "https://www.omdbapi.com/"
REQUEST_TIMEOUT_SECONDS = 20
BATCH_SIZE = 100

SESSION = requests.Session()


def fetch_pending_requests(client: bigquery.Client) -> list[dict[str, str]]:
    """Fetch pending requests from the BigQuery view of titles without an OMDb answer.

    Args:
        client: BigQuery client; the project comes from the environment.

    Returns:
        OMDb query parameters, one dict per request. The API key is never part of them.
    """
    query = """
        select requested_title
        from intermediate.int_omdb_requests_to_fetch
        order by requested_title
    """
    rows = client.query(query).result()
    return [{"t": row["requested_title"], "type": "movie"} for row in rows]


def fetch_movie(request: dict[str, str], api_key: str) -> dict[str, Any]:
    """Fetch movie from OMDb API.

    Args:
        request: Query parameters from `fetch_pending_requests`.
        api_key: OMDb API key; sent with the request but never saved.

    Returns:
        Parsed OMDb response body, including "Movie not found!", which OMDb sends with 200.

    Raises:
        requests.RequestException: No usable answer from OMDb, such as a timeout or 401 for a bad key.
        ValueError: Response body that is not JSON.
    """
    # A copy, so the key never lands in the request that gets saved.
    params = dict(request)
    params["apikey"] = api_key

    response = SESSION.get(OMDB_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return json.loads(response.content)


def build_omdb_row(
    request: dict[str, str], omdb_response: dict[str, Any]
) -> dict[str, Any]:
    """Build OMDb row for one request: one line of the NDJSON batch file.

    Args:
        request: Query parameters sent to OMDb. The API key is never part of them.
        omdb_response: Response from `fetch_movie`.

    Returns:
        Row with the request, the fetch time and the OMDb response.
    """
    return {
        "request": request,
        "fetched_at": datetime.now(UTC).isoformat(),
        "response": omdb_response,
    }


def load_batch_to_gcs(
    bucket: storage.Bucket,
    run_started_at: str,
    batch_number: int,
    rows: list[dict[str, Any]],
) -> None:
    """Load batch to GCS as one NDJSON file under the omdb prefix.

    Args:
        bucket: Landing bucket read by the raw.omdb external table.
        run_started_at: Start time of this run, shared by all its files.
        batch_number: Position of the batch in the run, starting at 1.
        rows: Rows from `build_omdb_row`.
    """
    # ensure_ascii=False keeps letters like "é" instead of writing their codes.
    content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    blob = bucket.blob(f"omdb/{run_started_at}-{batch_number:04d}.ndjson")
    blob.upload_from_string(content, content_type="application/x-ndjson")


def run_fetch_movies(limit: int | None = None) -> None:
    """Run fetch movies for every pending request, writing batches to GCS.

    Nothing is saved for a failed request, so the view returns it again next run.

    Args:
        limit: Maximum number of requests to fetch; all of them when None.
    """
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        raise ValueError("OMDB_API_KEY not set")
    bucket = storage.Client().bucket(os.environ["GCS_LANDING_BUCKET"])

    todo = fetch_pending_requests(bigquery.Client())
    if limit is not None:
        todo = todo[:limit]
    print(f"{len(todo)} requests to fetch now")

    run_started_at = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rows: list[dict[str, Any]] = []
    batches = 0
    failed = 0
    for number, request in enumerate(todo, start=1):
        try:
            omdb_response = fetch_movie(request, api_key)
        except requests.HTTPError as error:
            # 401 means a wrong key or no requests left for today
            if error.response is not None and error.response.status_code == 401:
                raise SystemExit("OMDb answered 401, stopping the run") from error
            failed += 1
            print(f"failed: {request['t']!r} ({type(error).__name__})")
            continue
        except (requests.RequestException, ValueError) as error:
            failed += 1
            # Only the error type: the full message includes the URL with the API key.
            print(f"failed: {request['t']!r} ({type(error).__name__})")
            continue
        rows.append(build_omdb_row(request, omdb_response))
        if len(rows) == BATCH_SIZE:
            batches += 1
            load_batch_to_gcs(bucket, run_started_at, batches, rows)
            rows = []
            print(f"{number} / {len(todo)}")

    if rows:
        batches += 1
        load_batch_to_gcs(bucket, run_started_at, batches, rows)

    print(f"done: {len(todo) - failed} written in {batches} files, {failed} failed")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_fetch_movies(limit)
