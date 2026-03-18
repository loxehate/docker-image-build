#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import json
import logging
import random
import time
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

import click
import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from strenum import StrEnum


class LaunchMode(StrEnum):
    SELF_HOST = "self-host"
    HOST = "host"


class Transport(StrEnum):
    SSE = "sse"
    STEAMABLE_HTTP = "streamable-http"


BASE_URL = "http://127.0.0.1:9380"
HOST = "127.0.0.1"
PORT = "9382"
HOST_API_KEY = ""
MODE = ""
TRANSPORT_SSE_ENABLED = True
TRANSPORT_STREAMABLE_HTTP_ENABLED = True
JSON_RESPONSE = True


class RAGFlowConnector:
    _MAX_DATASET_CACHE = 32
    _CACHE_TTL = 300

    _dataset_metadata_cache: OrderedDict[str, tuple[dict, float | int]] = OrderedDict()  # "dataset_id" -> (metadata, expiry_ts)
    _document_metadata_cache: OrderedDict[str, tuple[list[tuple[str, dict]], float | int]] = OrderedDict()  # "dataset_id" -> ([(document_id, doc_metadata)], expiry_ts)

    def __init__(self, base_url: str, version="v1"):
        self.base_url = base_url
        self.version = version
        self.api_url = f"{self.base_url}/api/{self.version}"
        self._async_client = None

    async def _get_client(self):
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self._async_client

    async def close(self):
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    async def _post(self, path, json=None, stream=False, files=None, api_key: str = ""):
        if not api_key:
            return None
        client = await self._get_client()
        res = await client.post(url=self.api_url + path, json=json, headers={"Authorization": f"Bearer {api_key}"})
        return res

    async def _get(self, path, params=None, api_key: str = ""):
        if not api_key:
            return None
        client = await self._get_client()
        res = await client.get(url=self.api_url + path, params=params, headers={"Authorization": f"Bearer {api_key}"})
        return res

    @staticmethod
    def _parse_json_response(res):
        if not res or res.status_code != 200:
            raise Exception([types.TextContent(type="text", text="Cannot process this operation.")])

        payload = res.json()
        if payload.get("code") != 0:
            raise Exception([types.TextContent(type="text", text=payload.get("message", "Cannot process this operation."))])
        return payload

    @staticmethod
    def _dedupe_preserve_order(values: list[str] | None) -> list[str]:
        if not values:
            return []

        seen = set()
        ordered_values = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            ordered_values.append(value)
        return ordered_values

    def _is_cache_valid(self, ts):
        return time.time() < ts

    def _get_expiry_timestamp(self):
        offset = random.randint(-30, 30)
        return time.time() + self._CACHE_TTL + offset

    def _get_cached_dataset_metadata(self, dataset_id):
        entry = self._dataset_metadata_cache.get(dataset_id)
        if entry:
            data, ts = entry
            if self._is_cache_valid(ts):
                self._dataset_metadata_cache.move_to_end(dataset_id)
                return data
        return None

    def _set_cached_dataset_metadata(self, dataset_id, metadata):
        self._dataset_metadata_cache[dataset_id] = (metadata, self._get_expiry_timestamp())
        self._dataset_metadata_cache.move_to_end(dataset_id)
        if len(self._dataset_metadata_cache) > self._MAX_DATASET_CACHE:
            self._dataset_metadata_cache.popitem(last=False)

    def _get_cached_document_metadata_by_dataset(self, dataset_id):
        entry = self._document_metadata_cache.get(dataset_id)
        if entry:
            data_list, ts = entry
            if self._is_cache_valid(ts):
                self._document_metadata_cache.move_to_end(dataset_id)
                return {doc_id: doc_meta for doc_id, doc_meta in data_list}
        return None

    def _set_cached_document_metadata_by_dataset(self, dataset_id, doc_id_meta_list):
        self._document_metadata_cache[dataset_id] = (doc_id_meta_list, self._get_expiry_timestamp())
        self._document_metadata_cache.move_to_end(dataset_id)

    async def list_datasets(
        self,
        *,
        api_key: str,
        page: int = 1,
        page_size: int = 1000,
        orderby: str = "create_time",
        desc: bool = True,
        id: str | None = None,
        name: str | None = None,
    ):
        params = {"page": page, "page_size": page_size, "orderby": orderby, "desc": desc}
        if id:
            params['id'] = id
        if name :
            params['name'] = name

        datasets = await self.list_datasets_raw(api_key=api_key, **params)
        result_list = []
        for data in datasets:
            d = {"name": data["name"], "description": data["description"], "id": data["id"]}
            result_list.append(json.dumps(d, ensure_ascii=False))
        return "\n".join(result_list)

    async def list_datasets_raw(
        self,
        *,
        api_key: str,
        page: int = 1,
        page_size: int = 1000,
        orderby: str = "create_time",
        desc: bool = True,
        id: str | None = None,
        name: str | None = None,
    ) -> list[dict]:
        params = {"page": page, "page_size": page_size, "orderby": orderby, "desc": desc}
        if id:
            params["id"] = id
        if name:
            params["name"] = name

        payload = self._parse_json_response(await self._get("/datasets", params, api_key=api_key))
        datasets = []
        for data in payload.get("data", []):
            datasets.append(
                {
                    "id": data.get("id", ""),
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "document_count": data.get("document_count"),
                    "chunk_count": data.get("chunk_count"),
                    "create_date": data.get("create_date", ""),
                    "update_date": data.get("update_date", ""),
                    "avatar": data.get("avatar", ""),
                    "language": data.get("language", ""),
                    "embedding_model": data.get("embedding_model", ""),
                    "permission": data.get("permission", ""),
                }
            )
        return datasets

    async def resolve_dataset_ids(
        self,
        *,
        api_key: str,
        dataset_ids: list[str] | None = None,
        dataset_names: list[str] | None = None,
    ) -> list[str]:
        resolved_ids = self._dedupe_preserve_order(dataset_ids)
        requested_names = self._dedupe_preserve_order(dataset_names)
        if requested_names:
            datasets = await self.list_datasets_raw(api_key=api_key)
            lower_name_to_ids = {}
            for dataset in datasets:
                dataset_name = (dataset.get("name") or "").strip()
                dataset_id = dataset.get("id")
                if not dataset_name or not dataset_id:
                    continue
                lower_name_to_ids.setdefault(dataset_name.lower(), []).append(dataset_id)

            missing_names = []
            for dataset_name in requested_names:
                matched_ids = lower_name_to_ids.get(dataset_name.lower())
                if not matched_ids:
                    missing_names.append(dataset_name)
                    continue
                resolved_ids.extend(matched_ids)

            if missing_names:
                raise ValueError(f"Dataset(s) not found: {', '.join(missing_names)}")

        if not resolved_ids:
            datasets = await self.list_datasets_raw(api_key=api_key)
            resolved_ids = [dataset["id"] for dataset in datasets if dataset.get("id")]

        return self._dedupe_preserve_order(resolved_ids)

    async def list_documents(
        self,
        *,
        api_key: str,
        dataset_ids: list[str] | None = None,
        dataset_names: list[str] | None = None,
        document_ids: list[str] | None = None,
        document_names: list[str] | None = None,
        force_refresh: bool = False,
    ) -> list[dict]:
        resolved_dataset_ids = await self.resolve_dataset_ids(api_key=api_key, dataset_ids=dataset_ids, dataset_names=dataset_names)
        document_cache, dataset_cache = await self._get_document_metadata_cache(
            resolved_dataset_ids,
            api_key=api_key,
            force_refresh=force_refresh,
        )

        requested_document_ids = set(self._dedupe_preserve_order(document_ids))
        requested_document_names = {name.lower(): name for name in self._dedupe_preserve_order(document_names)}
        documents = []
        for document in document_cache.values():
            if requested_document_ids and document.get("document_id") not in requested_document_ids:
                continue
            document_name = (document.get("name") or "").strip()
            if requested_document_names and document_name.lower() not in requested_document_names:
                continue

            dataset_id = document.get("dataset_id")
            dataset_meta = dataset_cache.get(dataset_id, {})
            documents.append(
                {
                    **document,
                    "dataset_name": dataset_meta.get("name", "Unknown"),
                    "dataset_description": dataset_meta.get("description", ""),
                }
            )

        if requested_document_names:
            found_names = {(document.get("name") or "").strip().lower() for document in documents}
            missing_names = [original_name for lowered_name, original_name in requested_document_names.items() if lowered_name not in found_names]
            if missing_names:
                raise ValueError(f"Document(s) not found: {', '.join(missing_names)}")

        if requested_document_ids:
            found_ids = {document.get("document_id") for document in documents}
            missing_ids = [document_id for document_id in requested_document_ids if document_id not in found_ids]
            if missing_ids:
                raise ValueError(f"Document ID(s) not found: {', '.join(missing_ids)}")

        documents.sort(key=lambda item: ((item.get("dataset_name") or "").lower(), (item.get("name") or "").lower(), item.get("document_id") or ""))
        return documents

    async def resolve_document_ids(
        self,
        *,
        api_key: str,
        dataset_ids: list[str],
        document_ids: list[str] | None = None,
        document_names: list[str] | None = None,
        force_refresh: bool = False,
    ) -> list[str]:
        resolved_document_ids = self._dedupe_preserve_order(document_ids)
        requested_document_names = self._dedupe_preserve_order(document_names)
        if not requested_document_names:
            return resolved_document_ids

        documents = await self.list_documents(
            api_key=api_key,
            dataset_ids=dataset_ids,
            document_ids=resolved_document_ids,
            document_names=requested_document_names,
            force_refresh=force_refresh,
        )
        resolved_document_ids.extend(document["document_id"] for document in documents if document.get("document_id"))
        return self._dedupe_preserve_order(resolved_document_ids)

    async def retrieval(
        self,
        *,
        api_key: str,
        dataset_ids,
        document_ids=None,
        question="",
        page=1,
        page_size=30,
        similarity_threshold=0.2,
        vector_similarity_weight=0.3,
        top_k=1024,
        rerank_id: str | None = None,
        keyword: bool = False,
        force_refresh: bool = False,
    ):
        if document_ids is None:
            document_ids = []
        if not dataset_ids:
            dataset_ids = await self.resolve_dataset_ids(api_key=api_key)

        data_json = {
            "page": page,
            "page_size": page_size,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "top_k": top_k,
            "rerank_id": rerank_id,
            "keyword": keyword,
            "question": question,
            "dataset_ids": dataset_ids,
            "document_ids": document_ids,
        }
        # Send a POST request to the backend service (using requests library as an example, actual implementation may vary)
        payload = self._parse_json_response(await self._post("/retrieval", json=data_json, api_key=api_key))
        if payload.get("code") == 0:
            data = payload["data"]
            chunks = []

            # Cache document metadata and dataset information
            document_cache, dataset_cache = await self._get_document_metadata_cache(dataset_ids, api_key=api_key, force_refresh=force_refresh)

            # Process chunks with enhanced field mapping including per-chunk metadata
            for chunk_data in data.get("chunks", []):
                enhanced_chunk = self._map_chunk_fields(chunk_data, dataset_cache, document_cache)
                chunks.append(enhanced_chunk)

            # Build structured response (no longer need response-level document_metadata)
            response = {
                "chunks": chunks,
                "pagination": {
                    "page": data.get("page", page),
                    "page_size": data.get("page_size", page_size),
                    "total_chunks": data.get("total", len(chunks)),
                    "total_pages": (data.get("total", len(chunks)) + page_size - 1) // page_size,
                },
                "query_info": {
                    "question": question,
                    "similarity_threshold": similarity_threshold,
                    "vector_weight": vector_similarity_weight,
                    "keyword_search": keyword,
                    "dataset_count": len(dataset_ids),
                },
            }

            return [types.TextContent(type="text", text=json.dumps(response, ensure_ascii=False))]

        raise Exception([types.TextContent(type="text", text=payload.get("message"))])

    async def _get_document_metadata_cache(self, dataset_ids, *, api_key: str, force_refresh=False):
        """Cache document metadata for all documents in the specified datasets"""
        document_cache = {}
        dataset_cache = {}

        try:
            for dataset_id in dataset_ids:
                dataset_meta = None if force_refresh else self._get_cached_dataset_metadata(dataset_id)
                if not dataset_meta:
                    # First get dataset info for name
                    dataset_res = await self._get("/datasets", {"id": dataset_id, "page_size": 1}, api_key=api_key)
                    if dataset_res and dataset_res.status_code == 200:
                        dataset_data = dataset_res.json()
                        if dataset_data.get("code") == 0 and dataset_data.get("data"):
                            dataset_info = dataset_data["data"][0]
                            dataset_meta = {"name": dataset_info.get("name", "Unknown"), "description": dataset_info.get("description", "")}
                            self._set_cached_dataset_metadata(dataset_id, dataset_meta)
                if dataset_meta:
                    dataset_cache[dataset_id] = dataset_meta

                docs = None if force_refresh else self._get_cached_document_metadata_by_dataset(dataset_id)
                if docs is None:
                    page = 1
                    page_size = 30
                    doc_id_meta_list = []
                    docs = {}
                    while page:
                        docs_res = await self._get(f"/datasets/{dataset_id}/documents?page={page}", api_key=api_key)
                        if not docs_res:
                            break
                        docs_data = docs_res.json()
                        if docs_data.get("code") == 0 and docs_data.get("data", {}).get("docs"):
                            for doc in docs_data["data"]["docs"]:
                                doc_id = doc.get("id")
                                if not doc_id:
                                    continue
                                doc_meta = {
                                    "document_id": doc_id,
                                    "name": doc.get("name", ""),
                                    "location": doc.get("location", ""),
                                    "type": doc.get("type", ""),
                                    "size": doc.get("size"),
                                    "chunk_count": doc.get("chunk_count"),
                                    "create_date": doc.get("create_date", ""),
                                    "update_date": doc.get("update_date", ""),
                                    "token_count": doc.get("token_count"),
                                    "thumbnail": doc.get("thumbnail", ""),
                                    "dataset_id": doc.get("dataset_id", dataset_id),
                                    "meta_fields": doc.get("meta_fields", {}),
                                }
                                doc_id_meta_list.append((doc_id, doc_meta))
                                docs[doc_id] = doc_meta

                            page += 1
                            if docs_data.get("data", {}).get("total", 0) - page * page_size <= 0:
                                page = None

                        self._set_cached_document_metadata_by_dataset(dataset_id, doc_id_meta_list)
                if docs:
                    document_cache.update(docs)

        except Exception as e:
            # Gracefully handle metadata cache failures
            logging.error(f"Problem building the document metadata cache: {str(e)}")
            pass

        return document_cache, dataset_cache

    def _map_chunk_fields(self, chunk_data, dataset_cache, document_cache):
        """Preserve all original API fields and add per-chunk document metadata"""
        # Start with ALL raw data from API (preserve everything like original version)
        mapped = dict(chunk_data)

        # Add dataset name enhancement
        dataset_id = chunk_data.get("dataset_id") or chunk_data.get("kb_id")
        if dataset_id and dataset_id in dataset_cache:
            mapped["dataset_name"] = dataset_cache[dataset_id]["name"]
        else:
            mapped["dataset_name"] = "Unknown"

        # Add document name convenience field
        mapped["document_name"] = chunk_data.get("document_keyword", "")

        # Add per-chunk document metadata
        document_id = chunk_data.get("document_id")
        if document_id and document_id in document_cache:
            mapped["document_metadata"] = document_cache[document_id]

        return mapped


class RAGFlowCtx:
    def __init__(self, connector: RAGFlowConnector):
        self.conn = connector


@asynccontextmanager
async def sse_lifespan(server: Server) -> AsyncIterator[dict]:
    ctx = RAGFlowCtx(RAGFlowConnector(base_url=BASE_URL))

    logging.info("Legacy SSE application started with StreamableHTTP session manager!")
    try:
        yield {"ragflow_ctx": ctx}
    finally:
        await ctx.conn.close()
        logging.info("Legacy SSE application shutting down...")


app = Server("ragflow-mcp-server", lifespan=sse_lifespan)
AUTH_TOKEN_STATE_KEY = "ragflow_auth_token"


def _to_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="ignore")
    return str(value)


def _extract_token_from_headers(headers: Any) -> str | None:
    if not headers or not hasattr(headers, "get"):
        return None

    auth_keys = ("authorization", "Authorization", b"authorization", b"Authorization")
    for key in auth_keys:
        auth = headers.get(key)
        if not auth:
            continue
        auth_text = _to_text(auth).strip()
        if auth_text.lower().startswith("bearer "):
            token = auth_text[7:].strip()
            if token:
                return token

    api_key_keys = ("api_key", "x-api-key", "Api-Key", "X-API-Key", b"api_key", b"x-api-key", b"Api-Key", b"X-API-Key")
    for key in api_key_keys:
        token = headers.get(key)
        if token:
            token_text = _to_text(token).strip()
            if token_text:
                return token_text

    return None


def _extract_token_from_request(request: Any) -> str | None:
    if request is None:
        return None

    state = getattr(request, "state", None)
    if state is not None:
        token = getattr(state, AUTH_TOKEN_STATE_KEY, None)
        if token:
            return token

    token = _extract_token_from_headers(getattr(request, "headers", None))
    if token and state is not None:
        setattr(state, AUTH_TOKEN_STATE_KEY, token)

    return token


def with_api_key(required: bool = True):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = app.request_context
            ragflow_ctx = ctx.lifespan_context.get("ragflow_ctx")
            if not ragflow_ctx:
                raise ValueError("Get RAGFlow Context failed")

            connector = ragflow_ctx.conn
            api_key = HOST_API_KEY

            if MODE == LaunchMode.HOST:
                api_key = _extract_token_from_request(getattr(ctx, "request", None)) or ""
                if required and not api_key:
                    raise ValueError("RAGFlow API key or Bearer token is required.")

            return await func(*args, connector=connector, api_key=api_key, **kwargs)

        return wrapper

    return decorator


@app.list_tools()
@with_api_key(required=True)
async def list_tools(*, connector: RAGFlowConnector, api_key: str) -> list[types.Tool]:
    dataset_description = await connector.list_datasets(api_key=api_key)

    return [
        types.Tool(
            name="ragflow_list_datasets",
            description="List the datasets currently available to the authenticated RAGFlow user, including dataset IDs, names, and descriptions. Use this when you need to discover valid datasets before retrieval.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Optional dataset name keyword filter.",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination.",
                        "default": 1,
                        "minimum": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of datasets returned per page.",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "orderby": {
                        "type": "string",
                        "description": "Dataset ordering field.",
                        "default": "create_time",
                    },
                    "desc": {
                        "type": "boolean",
                        "description": "Whether to sort in descending order.",
                        "default": True,
                    },
                },
            },
        ),
        types.Tool(
            name="ragflow_list_documents",
            description="List documents in one or more RAGFlow datasets. You can target datasets by ID or by human-readable dataset_names, and optionally filter documents by document_ids or document_names.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional dataset IDs to inspect. If omitted, all available datasets are used.",
                    },
                    "dataset_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional dataset names to resolve into dataset IDs before listing documents.",
                    },
                    "document_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional document IDs to filter the result.",
                    },
                    "document_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional document names to filter the result.",
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Set to true to bypass cached metadata and refetch dataset/document metadata.",
                        "default": False,
                    },
                },
            },
        ),
        types.Tool(
            name="ragflow_retrieval",
            description="Retrieve relevant chunks from the RAGFlow retrieve interface based on the question. You can optionally specify dataset_ids or dataset_names to limit the search scope, and document_ids or document_names to search inside specific files. When neither dataset_ids nor dataset_names is provided, the server automatically searches across ALL available datasets. Below is the list of all available datasets, including their descriptions and IDs:"
            + dataset_description,
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional array of dataset IDs to search. If not provided or empty, all datasets will be searched."},
                    "dataset_names": {"type": "array", "items": {"type": "string"}, "description": "Optional dataset names to search. Names are resolved case-insensitively before retrieval."},
                    "document_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional array of document IDs to search within."},
                    "document_names": {"type": "array", "items": {"type": "string"}, "description": "Optional document names to search within. Names are resolved case-insensitively within the selected datasets."},
                    "question": {"type": "string", "description": "The question or query to search for."},
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "default": 1,
                        "minimum": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return per page (default: 10, max recommended: 50 to avoid token limits)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "description": "Minimum similarity threshold for results",
                        "default": 0.2,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "vector_similarity_weight": {
                        "type": "number",
                        "description": "Weight for vector similarity vs term similarity",
                        "default": 0.3,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "keyword": {
                        "type": "boolean",
                        "description": "Enable keyword-based search",
                        "default": False,
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum results to consider before ranking",
                        "default": 1024,
                        "minimum": 1,
                        "maximum": 1024,
                    },
                    "rerank_id": {
                        "type": "string",
                        "description": "Optional reranking model identifier",
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Set to true only if fresh dataset and document metadata is explicitly required. Otherwise, cached metadata is used (default: false).",
                        "default": False,
                    },
                },
                "required": ["question"],
            },
        ),
    ]


@app.call_tool()
@with_api_key(required=True)
async def call_tool(
    name: str,
    arguments: dict,
    *,
    connector: RAGFlowConnector,
    api_key: str,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "ragflow_list_datasets":
        datasets = await connector.list_datasets_raw(
            api_key=api_key,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 100),
            orderby=arguments.get("orderby", "create_time"),
            desc=arguments.get("desc", True),
            name=arguments.get("name"),
        )
        return [types.TextContent(type="text", text=json.dumps({"datasets": datasets, "total": len(datasets)}, ensure_ascii=False))]

    if name == "ragflow_list_documents":
        documents = await connector.list_documents(
            api_key=api_key,
            dataset_ids=arguments.get("dataset_ids", []),
            dataset_names=arguments.get("dataset_names", []),
            document_ids=arguments.get("document_ids", []),
            document_names=arguments.get("document_names", []),
            force_refresh=arguments.get("force_refresh", False),
        )
        return [types.TextContent(type="text", text=json.dumps({"documents": documents, "total": len(documents)}, ensure_ascii=False))]

    if name == "ragflow_retrieval":
        force_refresh = arguments.get("force_refresh", False)
        dataset_ids = await connector.resolve_dataset_ids(
            api_key=api_key,
            dataset_ids=arguments.get("dataset_ids", []),
            dataset_names=arguments.get("dataset_names", []),
        )
        document_ids = await connector.resolve_document_ids(
            api_key=api_key,
            dataset_ids=dataset_ids,
            document_ids=arguments.get("document_ids", []),
            document_names=arguments.get("document_names", []),
            force_refresh=force_refresh,
        )
        question = arguments.get("question", "")
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 10)
        similarity_threshold = arguments.get("similarity_threshold", 0.2)
        vector_similarity_weight = arguments.get("vector_similarity_weight", 0.3)
        keyword = arguments.get("keyword", False)
        top_k = arguments.get("top_k", 1024)
        rerank_id = arguments.get("rerank_id")

        return await connector.retrieval(
            api_key=api_key,
            dataset_ids=dataset_ids,
            document_ids=document_ids,
            question=question,
            page=page,
            page_size=page_size,
            similarity_threshold=similarity_threshold,
            vector_similarity_weight=vector_similarity_weight,
            keyword=keyword,
            top_k=top_k,
            rerank_id=rerank_id,
            force_refresh=force_refresh,
        )
    raise ValueError(f"Tool not found: {name}")


def create_starlette_app():
    routes = []
    middleware = None
    if MODE == LaunchMode.HOST:
        from starlette.types import ASGIApp, Receive, Scope, Send

        class AuthMiddleware:
            def __init__(self, app: ASGIApp):
                self.app = app

            async def __call__(self, scope: Scope, receive: Receive, send: Send):
                if scope["type"] != "http":
                    await self.app(scope, receive, send)
                    return

                path = scope["path"]
                if path.startswith("/messages/") or path.startswith("/sse") or path.startswith("/mcp"):
                    headers = dict(scope["headers"])
                    token = _extract_token_from_headers(headers)

                    if not token:
                        response = JSONResponse({"error": "Missing or invalid authorization header"}, status_code=401)
                        await response(scope, receive, send)
                        return
                    scope.setdefault("state", {})[AUTH_TOKEN_STATE_KEY] = token

                await self.app(scope, receive, send)

        middleware = [Middleware(AuthMiddleware)]

    # Add SSE routes if enabled
    if TRANSPORT_SSE_ENABLED:
        from mcp.server.sse import SseServerTransport

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options(experimental_capabilities={"headers": dict(request.headers)}))
            return Response()

        routes.extend(
            [
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )

    # Add streamable HTTP route if enabled
    streamablehttp_lifespan = None
    if TRANSPORT_STREAMABLE_HTTP_ENABLED:
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.types import Receive, Scope, Send

        session_manager = StreamableHTTPSessionManager(
            app=app,
            event_store=None,
            json_response=JSON_RESPONSE,
            stateless=True,
        )

        class StreamableHTTPEntry:
            async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                await session_manager.handle_request(scope, receive, send)

        streamable_http_entry = StreamableHTTPEntry()

        @asynccontextmanager
        async def streamablehttp_lifespan(app: Starlette) -> AsyncIterator[None]:
            async with session_manager.run():
                logging.info("StreamableHTTP application started with StreamableHTTP session manager!")
                try:
                    yield
                finally:
                    logging.info("StreamableHTTP application shutting down...")

        routes.extend(
            [
                Route("/mcp", endpoint=streamable_http_entry, methods=["GET", "POST", "DELETE"]),
                Mount("/mcp", app=streamable_http_entry),
            ]
        )

    return Starlette(
        debug=True,
        routes=routes,
        middleware=middleware,
        lifespan=streamablehttp_lifespan,
    )


@click.command()
@click.option("--base-url", type=str, default="http://127.0.0.1:9380", help="API base URL for RAGFlow backend")
@click.option("--host", type=str, default="127.0.0.1", help="Host to bind the RAGFlow MCP server")
@click.option("--port", type=int, default=9382, help="Port to bind the RAGFlow MCP server")
@click.option(
    "--mode",
    type=click.Choice(["self-host", "host"]),
    default="self-host",
    help=("Launch mode:\n  self-host: run MCP for a single tenant (requires --api-key)\n  host: multi-tenant mode, users must provide Authorization headers"),
)
@click.option("--api-key", type=str, default="", help="API key to use when in self-host mode")
@click.option(
    "--transport-sse-enabled/--no-transport-sse-enabled",
    default=True,
    help="Enable or disable legacy SSE transport mode (default: enabled)",
)
@click.option(
    "--transport-streamable-http-enabled/--no-transport-streamable-http-enabled",
    default=True,
    help="Enable or disable streamable-http transport mode (default: enabled)",
)
@click.option(
    "--json-response/--no-json-response",
    default=True,
    help="Enable or disable JSON response mode for streamable-http (default: enabled)",
)
def main(base_url, host, port, mode, api_key, transport_sse_enabled, transport_streamable_http_enabled, json_response):
    import os

    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()

    def parse_bool_flag(key: str, default: bool) -> bool:
        val = os.environ.get(key, str(default))
        return str(val).strip().lower() in ("1", "true", "yes", "on")

    global BASE_URL, HOST, PORT, MODE, HOST_API_KEY, TRANSPORT_SSE_ENABLED, TRANSPORT_STREAMABLE_HTTP_ENABLED, JSON_RESPONSE
    BASE_URL = os.environ.get("RAGFLOW_MCP_BASE_URL", base_url)
    HOST = os.environ.get("RAGFLOW_MCP_HOST", host)
    PORT = os.environ.get("RAGFLOW_MCP_PORT", str(port))
    MODE = os.environ.get("RAGFLOW_MCP_LAUNCH_MODE", mode)
    HOST_API_KEY = os.environ.get("RAGFLOW_MCP_HOST_API_KEY", api_key)
    TRANSPORT_SSE_ENABLED = parse_bool_flag("RAGFLOW_MCP_TRANSPORT_SSE_ENABLED", transport_sse_enabled)
    TRANSPORT_STREAMABLE_HTTP_ENABLED = parse_bool_flag("RAGFLOW_MCP_TRANSPORT_STREAMABLE_ENABLED", transport_streamable_http_enabled)
    JSON_RESPONSE = parse_bool_flag("RAGFLOW_MCP_JSON_RESPONSE", json_response)

    if MODE == LaunchMode.SELF_HOST and not HOST_API_KEY:
        raise click.UsageError("--api-key is required when --mode is 'self-host'")

    if not TRANSPORT_STREAMABLE_HTTP_ENABLED and JSON_RESPONSE:
        JSON_RESPONSE = False

    print(
        r"""
__  __  ____ ____       ____  _____ ______     _______ ____
|  \/  |/ ___|  _ \     / ___|| ____|  _ \ \   / / ____|  _ \
| |\/| | |   | |_) |    \___ \|  _| | |_) \ \ / /|  _| | |_) |
| |  | | |___|  __/      ___) | |___|  _ < \ V / | |___|  _ <
|_|  |_|\____|_|        |____/|_____|_| \_\ \_/  |_____|_| \_\
        """,
        flush=True,
    )
    print(f"MCP launch mode: {MODE}", flush=True)
    print(f"MCP host: {HOST}", flush=True)
    print(f"MCP port: {PORT}", flush=True)
    print(f"MCP base_url: {BASE_URL}", flush=True)

    if not any([TRANSPORT_SSE_ENABLED, TRANSPORT_STREAMABLE_HTTP_ENABLED]):
        print("At least one transport should be enabled, enable streamable-http automatically", flush=True)
        TRANSPORT_STREAMABLE_HTTP_ENABLED = True

    if TRANSPORT_SSE_ENABLED:
        print("SSE transport enabled: yes", flush=True)
        print("SSE endpoint available at /sse", flush=True)
    else:
        print("SSE transport enabled: no", flush=True)

    if TRANSPORT_STREAMABLE_HTTP_ENABLED:
        print("Streamable HTTP transport enabled: yes", flush=True)
        print("Streamable HTTP endpoint available at /mcp", flush=True)
        if JSON_RESPONSE:
            print("Streamable HTTP mode: JSON response enabled", flush=True)
        else:
            print("Streamable HTTP mode: SSE over HTTP enabled", flush=True)
    else:
        print("Streamable HTTP transport enabled: no", flush=True)
        if JSON_RESPONSE:
            print("Warning: --json-response ignored because streamable transport is disabled.", flush=True)

    uvicorn.run(
        create_starlette_app(),
        host=HOST,
        port=int(PORT),
    )


if __name__ == "__main__":
    """
    Launch examples:

    1. Self-host mode with both SSE and Streamable HTTP (in JSON response mode) enabled (default):
        uv run mcp/server/server.py --host=127.0.0.1 --port=9382 \
            --base-url=http://127.0.0.1:9380 \
            --mode=self-host --api-key=ragflow-xxxxx

    2. Host mode (multi-tenant, clients must provide Authorization headers):
        uv run mcp/server/server.py --host=127.0.0.1 --port=9382 \
            --base-url=http://127.0.0.1:9380 \
            --mode=host

    3. Disable legacy SSE (only streamable HTTP will be active):
        uv run mcp/server/server.py --no-transport-sse-enabled \
            --mode=self-host --api-key=ragflow-xxxxx

    4. Disable streamable HTTP (only legacy SSE will be active):
        uv run mcp/server/server.py --no-transport-streamable-http-enabled \
            --mode=self-host --api-key=ragflow-xxxxx

    5. Use streamable HTTP with SSE-style events (disable JSON response):
        uv run mcp/server/server.py --transport-streamable-http-enabled --no-json-response \
            --mode=self-host --api-key=ragflow-xxxxx

    6. Disable both transports (for testing):
        uv run mcp/server/server.py --no-transport-sse-enabled --no-transport-streamable-http-enabled \
            --mode=self-host --api-key=ragflow-xxxxx
    """
    main()
