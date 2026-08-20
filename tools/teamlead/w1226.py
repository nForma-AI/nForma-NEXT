# control-plane/api/handlers/workloads.py

"""
Unified Workloads API - Platform-Agnostic Container Management

Provides a single, consistent API for managing containerized workloads across
GKE (Kubernetes workers), Akash deployments, and CronJobs without requiring
users to know or care about the underlying platform.

Operations:
- List: Get all workloads across all platforms
- Get/Describe: Detailed information about a specific workload
- Delete: Remove a workload
- Events: Audit trail and lifecycle events

Unified Workload ID Format:
- worker-{id}     → GKE worker deployment
- akash-{dseq}    → Akash deployment
- cron-{name}     → Kubernetes CronJob

This follows the same pattern as our unified logs, exec, and scaling APIs.
"""

import asyncio
import concurrent.futures
import contextlib
import functools
import json
import logging
import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Bounded fan-out for list_workloads (CodeRabbit #571).
#
# The platform helpers are sync Firestore/Kubernetes I/O offloaded with
# asyncio.to_thread. Two problems with the bare form:
#
#   1. to_thread uses the DEFAULT executor, shared with every other offload in the
#      process. This endpoint fans out up to 4 calls per request, so N concurrent
#      requests put 4N blocking calls into a pool sized min(32, cpu+4) -- they queue
#      behind each other and the endpoint degrades under exactly the concurrency the
#      offload was meant to survive.
#   2. Nothing bounds how long a helper runs. A wedged Firestore/k8s call holds its
#      worker thread indefinitely.
#
# So: a DEDICATED executor (this endpoint can never starve unrelated offloads, and vice
# versa) plus an overall deadline on the fan-out.
#
# HONEST LIMITATION: a Python thread cannot be cancelled. The deadline frees the event
# loop and returns 504 instead of hanging the request, but a wedged call still occupies
# its thread until it returns. That is why the executor is bounded and separate --
# leaked threads are contained here rather than starving the whole process. Real
# per-call deadlines belong at the client layer (see _FIRESTORE_TIMEOUT_S in
# handlers/scaling.py) and are tracked separately.
_LIST_FANOUT_TIMEOUT_S = 45.0
_LIST_FANOUT_MAX_WORKERS = 8
_list_fanout_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None


def _get_list_fanout_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Lazily create the dedicated executor (module import must not spawn threads)."""
    global _list_fanout_executor
    if _list_fanout_executor is None:
        _list_fanout_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=_LIST_FANOUT_MAX_WORKERS,
            thread_name_prefix="list-workloads",
        )
    return _list_fanout_executor


def _offload(func, *args):
    """Run a sync helper on the dedicated fan-out executor."""
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(_get_list_fanout_executor(), functools.partial(func, *args))


from auth import get_current_organization, require_cluster_scope
from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, Field

from services.akt_rate_service import get_akt_usd_rate

from compiler.core.pricing_constants import HOURS_PER_MONTH, PLATFORM_FEE_PER_VCPU_HOUR

# DFC provider classification: wallet address is the ground truth. The set used
# to live at config/dfc_providers.json, but commit 53065681 (Apr 2026) deleted
# that file and moved the source of truth to regions_detailed.yaml via
# dfc_access_guard.is_dfc_provider_address(). This module previously kept the
# old loader, which silently failed (try/except: pass) and left the set empty,
# misclassifying every DFC deployment as plain akash in /workloads listings.
from services.dfc_access_guard import is_dfc_provider_address


def _resolve_provider(data: dict) -> str:
    """Resolve provider for an Akash/DFC deployment using wallet address as ground truth."""
    # 1. Wallet address is cryptographic proof — check first
    addr = data.get("provider_address", "")
    if addr and is_dfc_provider_address(addr):
        return "dfc"
    # 2. Explicit provider field from Firestore (set by deployer)
    explicit = data.get("provider", "")
    if explicit:
        return explicit.lower()
    # 3. Fallback: derive from region_id prefix
    region_id = data.get("region_id", "")
    if region_id.startswith("dfc-"):
        return "dfc"
    return "akash"


logger = logging.getLogger(__name__)

# =============================================================================
# Workloads-list short-TTL cache (load-shedding for the k8s API server)
# =============================================================================
# list_workloads() does per-call k8s LISTs (deployments + services) plus Akash/LAT/
# cron queries. Under concurrent load (e.g. a full CI matrix = ~7 clusters each
# polling /workloads every few seconds) that floods the SHARED k8s API server →
# the handler slows/errors → the gateway 502s. A short-TTL in-process cache
# collapses a burst to one real fetch per TTL window per (cluster, filters).
#
# Env-gated, default DISABLED (TTL=0) so prod behavior is unchanged until enabled
# deliberately (canary-first). Staleness is bounded by the TTL (a few seconds),
# which is harmless for a list view — and unrelated to pod/exec/kill calls, which
# go through separate endpoints, so resilience/recovery tests are unaffected.
_WORKLOADS_CACHE_TTL_SEC = float(os.getenv("WORKLOADS_CACHE_TTL_SEC", "0") or "0")
_workloads_cache: Dict[tuple, tuple] = {}  # key -> (expires_at_monotonic, response_dict)

# =============================================================================
# Router Setup
# =============================================================================

workloads_router = APIRouter(
    prefix="/v1/organizations/{organization_id}/projects/{project_id}/clusters/{cluster_id}/workloads",
    tags=["workloads"],
    # Enforce caller-org == path-org (+ project/cluster scope) on every route. Without this
    # the routes trusted the attacker-controlled path org and never checked the caller's —
    # a cross-tenant exec/delete/scale hole. Admin/full-org keys pass unchanged.
    dependencies=[Depends(require_cluster_scope)],
)


# =============================================================================
# Unified Models (Extend existing models.py)
# =============================================================================


class UnifiedWorkloadSummary:
    """
    Summary information about a workload (for List operation).

    Minimal info to display in a list view.
    """

    def __init__(
        self,
        workload_id: str,
        workload_type: str,
        name: str,
        status: str,
        created_at: datetime,
        replicas: Optional[int] = None,
        image: Optional[str] = None,
        namespace: Optional[str] = None,
        **kwargs,
    ):
        self.workload_id = workload_id
        self.workload_type = workload_type
        self.name = name
        self.status = status
        self.created_at = created_at
        self.replicas = replicas
        self.image = image
        self.namespace = namespace
        self.metadata = kwargs

    # USD fields that must be rounded to 2 decimals at serialization time.
    # Accrued keeps 6 decimals (sub-cent running counter).
    _USD_2DP = {"price_per_month_usd", "platform_fee_usd", "total_cost_usd"}
    # accrued_cost_usd is NOT rounded per-deployment — rounding happens
    # only at the aggregated sum level (total_accrued_usd in the API handler).
    _USD_RAW = {"accrued_cost_usd"}

    def to_dict(self) -> Dict[str, Any]:
        if isinstance(self.created_at, str):
            created_at_str = self.created_at
        elif self.created_at is not None:
            created_at_str = self.created_at.isoformat()
        else:
            created_at_str = None
        # Round USD cost fields at the serialization boundary so every
        # consumer (frontend, CLI, billing) sees consistent cents.
        meta = {}
        for k, v in self.metadata.items():
            if v is not None and k in self._USD_2DP:
                meta[k] = round(v, 2)
            else:
                meta[k] = v
        return {
            "workload_id": self.workload_id,
            "workload_type": self.workload_type,
            "name": self.name,
            "status": self.status,
            "created_at": created_at_str,
            "replicas": self.replicas,
            "image": self.image,
            "namespace": self.namespace,
            **meta,
        }


class UnifiedWorkloadDetail:
    """
    Detailed information about a workload (for Get/Describe operation).

    Full resource details including configuration, status, and metrics.
    """

    def __init__(
        self,
        workload_id: str,
        workload_type: str,
        name: str,
        status: str,
        created_at: datetime,
        updated_at: Optional[datetime] = None,
        namespace: Optional[str] = None,
        replicas: Optional[int] = None,
        image: Optional[str] = None,
        resources: Optional[Dict[str, Any]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        health_status: Optional[str] = None,
        endpoints: Optional[List[str]] = None,
        **kwargs,
    ):
        self.workload_id = workload_id
        self.workload_type = workload_type
        self.name = name
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.namespace = namespace
        self.replicas = replicas
        self.image = image
        self.resources = resources or {}
        self.env_vars = env_vars or {}
        self.labels = labels or {}
        self.health_status = health_status
        self.endpoints = endpoints or []
        self.platform_specific = kwargs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "workload_type": self.workload_type,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "namespace": self.namespace,
            "replicas": self.replicas,
            "image": self.image,
            "resources": self.resources,
            "env_vars": self.env_vars,
            "labels": self.labels,
            "health_status": self.health_status,
            "endpoints": self.endpoints,
            "platform_specific": self.platform_specific,
        }


class UnifiedWorkloadEvent:
    """Event in workload lifecycle (for Events operation)"""

    def __init__(
        self,
        event_id: str,
        workload_id: str,
        timestamp: datetime,
        event_type: str,
        message: str,
        severity: str = "info",
        **kwargs,
    ):
        self.event_id = event_id
        self.workload_id = workload_id
        self.timestamp = timestamp
        self.event_type = event_type
        self.message = message
        self.severity = severity
        self.metadata = kwargs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "workload_id": self.workload_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "message": self.message,
            "severity": self.severity,
            **self.metadata,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_workload_id(workload_id: str) -> tuple[str, str]:
    """
    Parse workload_id to determine type and extract resource ID.

    Returns:
        Tuple of (workload_type, resource_id)

    Examples:
        worker-api-gateway → ("gke_worker", "api-gateway")
        akash-12345678 → ("akash_deployment", "12345678")
        cron-daily-backup → ("cronjob", "daily-backup")
        lat-vm_y9815XnZ0vEkd → ("lat_deployment", "vm_y9815XnZ0vEkd")
    """
    if workload_id.startswith("worker-"):
        return "gke_worker", workload_id[7:]
    elif workload_id.startswith("akash-"):
        return "akash_deployment", workload_id[6:]
    elif workload_id.startswith("cron-"):
        return "cronjob", workload_id[5:]
    elif workload_id.startswith("lat-"):
        # LAT (=DFN, Latitude.sh) — resource_id is either a vm_id (default,
        # opaque "vm_*"/"plan_*" token) or a bare-metal server_id (legacy).
        return "lat_deployment", workload_id[4:]
    else:
        # Legacy: assume worker if no prefix
        return "gke_worker", workload_id


# =============================================================================
# Unified Create Request Model
# =============================================================================


class UnifiedCreateWorkloadRequest(BaseModel):
    """
    Unified request model for creating workloads across all platforms.

    Platform is determined by workload_type parameter.
    Common fields are extracted and platform-specific fields are in platform_config.
    """

    workload_type: str = Field(..., description="Type of workload: 'gke_worker', 'akash_deployment', 'cronjob'")

    # Common fields across all platforms
    name: str = Field(
        ...,
        pattern="^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$",
        description="Workload name (DNS-safe, lowercase)",
    )
    image: str = Field(..., description="Container image")
    replicas: int = Field(
        default=1,
        ge=0,
        le=100,
        description="Number of replicas (0 = serverless for GKE)",
    )

    # Resources
    cpu_request: Optional[str] = Field(default="250m", description="CPU request (e.g., '250m', '1', '2.0')")
    memory_request: Optional[str] = Field(default="512Mi", description="Memory request (e.g., '512Mi', '2Gi', '4Gi')")
    cpu_limit: Optional[str] = Field(default=None, description="CPU limit (optional)")
    memory_limit: Optional[str] = Field(default=None, description="Memory limit (optional)")

    # Networking
    ports: Optional[List[int]] = Field(default=[80], description="List of ports to expose (default: [80])")

    # Environment
    env_vars: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")

    # Container runtime
    command: Optional[List[str]] = Field(default=None, description="Container command override")
    args: Optional[List[str]] = Field(default=None, description="Container arguments")

    # Labels (GKE/CronJobs only)
    labels: Optional[Dict[str, str]] = Field(default=None, description="Kubernetes labels (GKE/CronJobs only)")

    # Platform-specific configuration
    platform_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Platform-specific configuration (autoscaling, volumes, schedule, etc.)",
    )

    # Async webhook
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for async completion notification")


from models import AkashDeploymentStatus, CreateAkashDeploymentRequest, CreateWorkerRequest  # noqa: E402
from firestore_client_cache import get_client as _get_firestore_client

# =============================================================================
# Create Workload (Unified)
# =============================================================================


@workloads_router.post(
    "",
    summary="Create a new workload",
    description="""
Create a new workload on the specified platform.

**Supported Platforms:**
- GKE workers (workload_type: 'gke_worker')
- Akash deployments (workload_type: 'akash_deployment')
- CronJobs (workload_type: 'cronjob')

**Request Body:**
Unified request format with common fields and platform-specific configuration.

**Response:**
- 201 Created (GKE workers - synchronous)
- 202 Accepted (Akash/CronJobs - asynchronous)

Returns workload_id for tracking the new workload.
""",
    status_code=201,
)
async def create_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    request: UnifiedCreateWorkloadRequest,
    organization: Dict = Depends(get_current_organization),
):
    """
    Create a new workload on the specified platform.

    Routes to platform-specific create implementation based on workload_type.
    """
    logger.info(
        f"[{organization_id}] Creating workload: type={request.workload_type}, name={request.name}, image={request.image}"
    )

    # Route to platform-specific handler
    if request.workload_type == "gke_worker":
        result = await _create_gke_worker(organization_id, project_id, cluster_id, request)
    elif request.workload_type == "akash_deployment":
        result = await _create_akash_deployment(organization_id, project_id, cluster_id, request)
    elif request.workload_type == "cronjob":
        result = await _create_cronjob(organization_id, project_id, cluster_id, request)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workload type: {request.workload_type}. Supported: gke_worker, akash_deployment, cronjob",
        )

    return result


async def _create_gke_worker(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    request: UnifiedCreateWorkloadRequest,
) -> Dict[str, Any]:
    """Create GKE worker using existing workers.py handler"""
    from models import WorkerType

    from handlers.workers import create_worker

    # Map unified request to CreateWorkerRequest
    worker_request = CreateWorkerRequest(
        worker_id=request.name,
        worker_type=WorkerType.WORKER,  # Default, can be overridden in platform_config
        app_image=request.image,
        app_port=request.ports[0] if request.ports else 80,
        replicas=request.replicas,
        cpu_request=request.cpu_request or "250m",
        memory_request=request.memory_request or "512Mi",
        cpu_limit=request.cpu_limit or "1",
        memory_limit=request.memory_limit or "1Gi",
        env=request.env_vars or {},
        command=request.command,
        args=request.args,
        labels=request.labels,
        # Apply platform-specific config if provided
        **(request.platform_config or {}),
    )

    # Call existing worker creation logic
    # create_worker(tenant_id, request, organization) where tenant_id == cluster_id
    result = await create_worker(
        tenant_id=cluster_id,
        request=worker_request,
        organization={"organization_id": organization_id},
    )

    # Return unified response
    return {
        "workload_id": f"worker-{request.name}",
        "workload_type": "gke_worker",
        "name": request.name,
        "status": "creating",
        "created_at": datetime.utcnow().isoformat(),
        "message": "GKE worker deployment initiated",
        "details": result,
    }


async def _create_akash_deployment(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    request: UnifiedCreateWorkloadRequest,
) -> Dict[str, Any]:
    """Create Akash deployment using existing akash.py handler"""
    from models import AkashPlacementAttributes, AkashPricing, AkashResourceProfile

    from handlers.akash import create_akash_deployment

    # Parse resource requests (convert Kubernetes format to Akash)
    cpu_units = _parse_cpu_to_units(request.cpu_request or "250m")
    memory_size = request.memory_request or "512Mi"

    # Build platform config
    platform_cfg = request.platform_config or {}

    # Map unified request to CreateAkashDeploymentRequest
    akash_request = CreateAkashDeploymentRequest(
        worker_id=request.name,
        organization_id=organization_id,
        cluster_id=cluster_id,
        namespace=f"c-{cluster_id}",
        app_image=request.image,
        app_port=request.ports[0] if request.ports else 80,
        app_ports=request.ports if len(request.ports or []) > 1 else None,
        worker_count=request.replicas,
        resources=AkashResourceProfile(
            cpu_units=cpu_units,
            memory_size=memory_size,
            storage_size=platform_cfg.get("storage_size", "1Gi"),
            app_port=request.ports[0] if request.ports else 80,
        ),
        placement=AkashPlacementAttributes(**platform_cfg.get("placement", {})),
        pricing=AkashPricing(**platform_cfg.get("pricing", {})),
        env_vars=request.env_vars or {},
        app_command=request.command,
        app_args=request.args,
        webhook_url=request.webhook_url,
        provider_type=platform_cfg.get("provider_type", "akash"),
    )

    # Call existing Akash deployment logic
    result = await create_akash_deployment(
        organization_id=organization_id,
        project_id=project_id,
        cluster_id=cluster_id,
        request=akash_request,
        organization={"organization_id": organization_id},
    )

    # Generate deployment ID from result
    deployment_id = result.get("deployment_id") or result.get("dseq", "pending")

    # Return unified response (async)
    return {
        "workload_id": f"akash-{deployment_id}",
        "workload_type": "akash_deployment",
        "name": request.name,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "message": "Akash deployment submitted",
        "task_id": result.get("task_id"),
        "details": result,
    }


async def _create_cronjob(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    request: UnifiedCreateWorkloadRequest,
) -> Dict[str, Any]:
    """Create CronJob"""

    # Platform config must include schedule
    platform_cfg = request.platform_config or {}
    schedule = platform_cfg.get("schedule")

    if not schedule:
        raise HTTPException(
            status_code=400,
            detail="CronJob requires 'schedule' in platform_config (e.g., '0 2 * * *')",
        )

    # Build CronJob request
    cronjob_request = {
        "name": request.name,
        "schedule": schedule,
        "image": request.image,
        "command": request.command,
        "args": request.args,
        "env_vars": request.env_vars or {},
        "labels": request.labels or {},
        "resources": {
            "cpu_request": request.cpu_request or "250m",
            "memory_request": request.memory_request or "512Mi",
            "cpu_limit": request.cpu_limit,
            "memory_limit": request.memory_limit,
        },
        **platform_cfg,
    }

    # Call existing CronJob creation logic (if exists)
    # For now, return placeholder
    db = await _get_firestore_client(firestore)

    # Store CronJob metadata in Firestore
    cronjob_doc = {
        "name": request.name,
        "organization_id": organization_id,
        "project_id": project_id,
        "cluster_id": cluster_id,
        "namespace": f"c-{cluster_id}",
        "schedule": schedule,
        "image": request.image,
        "command": request.command,
        "args": request.args,
        "env_vars": request.env_vars or {},
        "labels": request.labels or {},
        "resources": cronjob_request["resources"],
        "status": "creating",
        "created_at": datetime.utcnow(),
    }

    db.collection("cronjobs").add(cronjob_doc)

    return {
        "workload_id": f"cron-{request.name}",
        "workload_type": "cronjob",
        "name": request.name,
        "status": "creating",
        "created_at": datetime.utcnow().isoformat(),
        "schedule": schedule,
        "message": "CronJob creation initiated",
    }


def _parse_cpu_to_units(cpu_request: str) -> float:
    """
    Convert Kubernetes CPU format to Akash CPU units.

    Examples:
    - "250m" → 0.25
    - "1" → 1.0
    - "2.5" → 2.5
    """
    if cpu_request.endswith("m"):
        # Millicores
        return float(cpu_request[:-1]) / 1000
    else:
        # Cores
        return float(cpu_request)


# =============================================================================
# List Workloads (Unified)
# =============================================================================


@workloads_router.get(
    "",
    summary="List all workloads",
    description="""
List all containerized workloads across GKE, Akash, and CronJobs.

Returns a unified view of all workloads in the cluster, regardless of platform.

**Query Filters:**
- `type`: Filter by workload type (gke_worker, akash_deployment, cronjob, or 'all')
- `status`: Filter by status (running, pending, failed, etc.)
- `limit`: Max results to return

**Response:**
Unified list of workloads with minimal info for list views.
""",
)
async def list_workloads(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    type: str = Query("all", description="Workload type filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    organization: Dict = Depends(get_current_organization),
):
    """
    List all workloads across all platforms.

    Aggregates workers, Akash deployments, and CronJobs into a single response.
    """
    logger.info(f"[{organization_id}] Listing workloads: cluster={cluster_id}, type={type}, status={status}, limit={limit}")

    # Short-TTL cache (load-shedding) — serve a recent response without re-hitting the
    # k8s API server when the same (cluster, filters) is polled rapidly. Disabled when
    # WORKLOADS_CACHE_TTL_SEC=0 (default).
    _cache_key = (organization_id, project_id, cluster_id, type, status, limit)
    if _WORKLOADS_CACHE_TTL_SEC > 0:
        _hit = _workloads_cache.get(_cache_key)
        if _hit and _hit[0] > time.monotonic():
            logger.info(f"[{organization_id}] workloads cache HIT cluster={cluster_id} (ttl={_WORKLOADS_CACHE_TTL_SEC}s)")
            return _hit[1]
    _t0 = time.monotonic()  # instrumentation: always measure handler latency

    workloads: List[UnifiedWorkloadSummary] = []

    # Determine which platforms to query
    query_gke = type in ("all", "gke_worker")
    query_akash = type in ("all", "akash_deployment")
    query_cron = type in ("all", "cronjob")
    query_lat = type in ("all", "lat_deployment")

    # Parallel fetch from all platforms. Each helper is a SYNC function (pure
    # Firestore/k8s I/O); offload each to a worker thread via asyncio.to_thread so
    # the blocking I/O runs in true parallel threads instead of on the single uvicorn
    # event loop (the API is --workers 1; inline sync Firestore here stalled the loop
    # -> pod NotReady -> canary gateway 502/time-outed every concurrent smoke).
    # `task_platforms` runs in lockstep with `tasks` so each gathered result can be
    # attributed back to the platform that produced it. Without it the aggregate loop
    # below knows only THAT something failed, never WHICH platform — and the caller is
    # told nothing at all (see the `platforms` block after the gather).
    tasks = []
    task_platforms: List[str] = []

    if query_gke:
        tasks.append(_offload(_list_gke_workers, organization_id, project_id, cluster_id, status))
        task_platforms.append("gke")
    if query_akash:
        # _list_akash_deployments needs the AKT/USD rate. Fetch it INSIDE the akash
        # task so a pricing failure is isolated to just the akash result (gather uses
        # return_exceptions=True) instead of taking down the whole endpoint.
        async def _list_akash_with_rate() -> List[UnifiedWorkloadSummary]:
            rate = await get_akt_usd_rate()
            return await _offload(_list_akash_deployments, organization_id, project_id, cluster_id, status, rate)

        tasks.append(_list_akash_with_rate())
        task_platforms.append("akash")
    if query_cron:
        tasks.append(_offload(_list_cronjobs, organization_id, project_id, cluster_id, status))
        task_platforms.append("cronjob")
    if query_lat:
        tasks.append(_offload(_list_lat_deployments, organization_id, project_id, cluster_id, status))
        task_platforms.append("lat")

    # Execute all queries in parallel (across the dedicated fan-out executor), under an
    # overall deadline so a wedged platform call returns 504 rather than hanging the
    # request forever. return_exceptions=True keeps one platform's failure from taking
    # down the others; the timeout covers the case where a platform never answers at all.
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=_LIST_FANOUT_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.error(
            "list_workloads: platform fan-out exceeded %ss (org=%s cluster=%s)",
            _LIST_FANOUT_TIMEOUT_S,
            organization_id,
            cluster_id,
        )
        raise HTTPException(
            status_code=504,
            detail=f"Timed out listing workloads after {_LIST_FANOUT_TIMEOUT_S:.0f}s",
        ) from None

    # Aggregate results.
    #
    # ★ A platform whose query RAISED contributes nothing, exactly like a platform that
    # genuinely has nothing — and the response used to be byte-identical in both cases.
    # That ambiguity is not theoretical: E1's phase 3 reads this endpoint to count mesh
    # datacenters, and on run 31798178998 it concluded "GKE primary missing" from a list
    # containing only DFC entries while the cluster reported {'total': 3, 'ready': 3}.
    # From the response alone it is impossible to tell whether the GKE arm answered
    # "none" or never answered. `platforms` below records which, per platform, so the
    # caller can distinguish "we looked and found nothing" from "we could not look".
    platforms: Dict[str, Dict[str, Any]] = {
        name: {"queried": False, "ok": None, "count": 0, "error": None} for name in ("gke", "akash", "cronjob", "lat")
    }
    for platform_name, result in zip(task_platforms, results):
        entry = platforms[platform_name]
        entry["queried"] = True
        if isinstance(result, Exception):
            # NOTE: `type` is shadowed by this handler's query parameter, so the class
            # name must come from `__class__` — `type(result)` would raise TypeError.
            entry["ok"] = False
            entry["error"] = f"{result.__class__.__name__}: {result}"
            logger.error(f"[{organization_id}] Platform query failed ({platform_name}): {result}")
            continue
        entry["ok"] = True
        # Pre-`limit` contribution: what this platform actually returned, before the
        # global sort/truncate below. A caller checking "did GKE have anything" needs
        # the platform's own answer, not its share of a truncated page.
        entry["count"] = len(result)
        workloads.extend(result)

    degraded = sorted(name for name, entry in platforms.items() if entry["ok"] is False)

    # Sort by created_at (newest first)
    # Normalize all datetimes to UTC-aware to avoid "can't compare offset-naive and offset-aware" TypeError
    def _sort_key(w):
        try:
            dt = datetime.fromisoformat(w.created_at) if isinstance(w.created_at, str) else w.created_at
            if dt is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    workloads.sort(key=_sort_key, reverse=True)

    # Apply limit
    workloads = workloads[:limit]

    response = {
        "workloads": [w.to_dict() for w in workloads],
        "total": len(workloads),
        "filters": {
            "type": type,
            "status": status,
            "limit": limit,
        },
        # Per-platform outcome. `complete` is the one-field version: False means at
        # least one platform errored, so `workloads` is a PARTIAL list and its absences
        # prove nothing. Callers that conclude something from a missing entry must
        # check this first.
        "platforms": platforms,
        "degraded_platforms": degraded,
        "complete": not degraded,
    }
    if _WORKLOADS_CACHE_TTL_SEC > 0:
        _workloads_cache[_cache_key] = (time.monotonic() + _WORKLOADS_CACHE_TTL_SEC, response)
    # Instrumentation: handler latency + count (structured, one line, no per-object dumps)
    logger.info(
        f"[{organization_id}] workloads handler MISS cluster={cluster_id} "
        f"n={len(workloads)} dur_ms={(time.monotonic() - _t0) * 1000:.0f} "
        f"degraded={degraded or None} "
        f"cache_ttl={_WORKLOADS_CACHE_TTL_SEC}"
    )
    return response


def _list_gke_workers(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    status_filter: Optional[str],
) -> List[UnifiedWorkloadSummary]:
    """List GKE workers from Firestore (gke_deployments primary, workers legacy fallback)"""
    try:
        db = firestore.Client()

        workers = []
        seen_worker_ids: set = set()

        # Primary: gke_deployments collection (canonical source for all GKE worker data)
        try:
            gke_query = (
                db.collection("gke_deployments")
                .where("organization_id", "==", organization_id)
                .where("cluster_id", "==", cluster_id)
            )
            if status_filter:
                gke_query = gke_query.where("status", "==", status_filter)

            for doc in gke_query.stream():
                data = doc.to_dict()
                worker_id = data.get("worker_id") or doc.id
                workload_id = f"worker-{worker_id}"
                service_uris = data.get("service_uris") or []
                # If no service_uris in Firestore, try live K8s LB lookup
                if not service_uris:
                    try:
                        ns = data.get("namespace")
                        if ns:
                            core_api = k8s_client.CoreV1Api()
                            svcs = core_api.list_namespaced_service(
                                namespace=ns,
                                label_selector=f"worker-id={worker_id},df.io/loadbalancer=true",
                            )
                            for svc in svcs.items:
                                if svc.status and svc.status.load_balancer and svc.status.load_balancer.ingress:
                                    for ing in svc.status.load_balancer.ingress:
                                        if ing.ip:
                                            service_uris.append(f"http://{ing.ip}")
                                        elif ing.hostname:
                                            service_uris.append(f"http://{ing.hostname}")
                            if service_uris:
                                logger.info(
                                    f"[{organization_id}] Enriched GKE worker {worker_id} with live LB URI: {service_uris}"
                                )
                                # Backfill Firestore so next call is fast
                                doc.reference.update({"service_uris": service_uris})
                    except Exception as _lb_err:
                        logger.debug(f"[{organization_id}] K8s LB lookup for {worker_id} failed (non-fatal): {_lb_err}")

                workload = UnifiedWorkloadSummary(
                    workload_id=workload_id,
                    workload_type="gke_worker",
                    name=worker_id,
                    status=data.get("status", "unknown"),
                    created_at=data.get("created_at"),
                    replicas=None,
                    image=data.get("image"),
                    namespace=data.get("namespace"),
                    worker_type="deployment",
                    service_uris=service_uris,
                    region_id=data.get("region_id"),
                    provider=data.get("provider", "gcp"),
                )
                workers.append(workload)
                seen_worker_ids.add(workload_id)
                logger.debug(f"[{organization_id}] Found GKE worker {worker_id} via gke_deployments (canonical)")

            if workers:
                logger.info(f"[{organization_id}] Found {len(workers)} GKE worker(s) via gke_deployments (canonical)")
        except Exception as e:
            logger.warning(f"[{organization_id}] gke_deployments query failed (non-fatal): {e}")

        # Legacy fallback: workers collection (for pre-unification deploys)
        # Also includes namespace-based query for very old docs that used namespace instead of cluster_id.
        _workers_before_legacy = len(workers)
        try:
            query = (
                db.collection("workers").where("organization_id", "==", organization_id).where("cluster_id", "==", cluster_id)
            )
            if status_filter:
                query = query.where("status", "==", status_filter)

            for doc in query.stream():
                data = doc.to_dict()
                worker_id = data.get("worker_id") or doc.id
                workload_id = f"worker-{worker_id}"
                if workload_id in seen_worker_ids:
                    continue  # Already found in gke_deployments — skip duplicate
                workload = UnifiedWorkloadSummary(
                    workload_id=workload_id,
                    workload_type="gke_worker",
                    name=data.get("name") or worker_id,
                    status=data.get("status", "unknown"),
                    created_at=data.get("created_at"),
                    replicas=data.get("replicas"),
                    image=data.get("image"),
                    namespace=data.get("namespace"),
                    worker_type=data.get("worker_type"),
                    service_uris=data.get("service_uris") or [],
                )
                workers.append(workload)
                seen_worker_ids.add(workload_id)
                logger.debug(f"[{organization_id}] Found GKE worker {worker_id} via workers collection (legacy)")

            # Namespace fallback for very old docs that used namespace instead of cluster_id
            if len(workers) == _workers_before_legacy:
                query_ns = (
                    db.collection("workers")
                    .where("organization_id", "==", organization_id)
                    .where("namespace", "==", cluster_id)
                )
                if status_filter:
                    query_ns = query_ns.where("status", "==", status_filter)

                for doc in query_ns.stream():
                    data = doc.to_dict()
                    worker_id = data.get("worker_id") or doc.id
                    workload_id = f"worker-{worker_id}"
                    if workload_id in seen_worker_ids:
                        continue
                    workload = UnifiedWorkloadSummary(
                        workload_id=workload_id,
                        workload_type="gke_worker",
                        name=data.get("name") or worker_id,
                        status=data.get("status", "unknown"),
                        created_at=data.get("created_at"),
                        replicas=data.get("replicas"),
                        image=data.get("image"),
                        namespace=data.get("namespace"),
                        worker_type=data.get("worker_type"),
                        service_uris=data.get("service_uris") or [],
                    )
                    workers.append(workload)
                    seen_worker_ids.add(workload_id)
                    logger.debug(f"[{organization_id}] Found worker {worker_id} via namespace fallback (legacy)")

            _added_from_legacy = len(workers) - _workers_before_legacy
            if _added_from_legacy > 0:
                logger.info(f"[{organization_id}] Found {_added_from_legacy} GKE worker(s) via workers collection (legacy)")
        except Exception as e:
            logger.warning(f"[{organization_id}] workers collection query failed (non-fatal): {e}")

        # Fallback 3: query K8s directly for deployments in the cluster namespace
        # Last resort: GKE deployments may not write to any Firestore collection yet
        if not workers:
            try:
                # Look up actual namespace from entities_clusters collection
                # Document ID format: {org_id}--{project_id}--{cluster_id}
                doc_id = f"{organization_id}--{project_id}--{cluster_id}"
                cluster_doc = db.collection("entities_clusters").document(doc_id).get()
                if cluster_doc.exists:
                    namespace = cluster_doc.to_dict().get("namespace", f"c-{cluster_id}")
                    logger.info(f"[{organization_id}] K8s fallback: found namespace {namespace} from entities_clusters")
                else:
                    namespace = f"c-{cluster_id}"
                    logger.warning(f"[{organization_id}] K8s fallback: cluster doc {doc_id} not found, using {namespace}")
                apps_api = k8s_client.AppsV1Api()
                # Infrastructure services that should never appear as user workloads
                _INFRA_DEPLOYMENTS = {
                    "edge-envoy",
                    "consul-server",
                    "consul-mesh-gateway",
                    "prometheus-metrics",
                    "kamailio-sip-proxy",
                    "rtpengine",
                    "keydb-rtpengine",
                }
                deployments = apps_api.list_namespaced_deployment(namespace=namespace)
                for dep in deployments.items:
                    dep_name = dep.metadata.name
                    if dep_name in _INFRA_DEPLOYMENTS:
                        continue  # Skip infrastructure — only return user workloads
                    dep_replicas = dep.spec.replicas or 0
                    dep_available = (dep.status.available_replicas or 0) if dep.status else 0
                    dep_image = ""
                    if dep.spec.template.spec.containers:
                        dep_image = dep.spec.template.spec.containers[0].image or ""
                    dep_status = "active" if dep_available > 0 else "pending"
                    if status_filter and dep_status != status_filter:
                        continue
                    created_at = dep.metadata.creation_timestamp
                    # Extract service URIs from the worker's LB service.
                    # GKE workers use app=worker + worker-id={worker_id} labels (not app={dep_name}).
                    # The LB service is named {worker_id}-lb; use worker-id label selector.
                    service_uris = []
                    try:
                        core_api = k8s_client.CoreV1Api()
                        # Strip "worker-" prefix to get the worker_id for the label selector
                        lb_worker_id = dep_name[len("worker-") :] if dep_name.startswith("worker-") else dep_name
                        services = core_api.list_namespaced_service(
                            namespace=namespace,
                            label_selector=f"worker-id={lb_worker_id},df.io/loadbalancer=true",
                        )
                        for svc in services.items:
                            if svc.status and svc.status.load_balancer and svc.status.load_balancer.ingress:
                                for ing in svc.status.load_balancer.ingress:
                                    if ing.ip:
                                        service_uris.append(f"http://{ing.ip}")
                                    elif ing.hostname:
                                        service_uris.append(f"https://{ing.hostname}")
                    except Exception:
                        pass  # Service lookup is best-effort
                    workload = UnifiedWorkloadSummary(
                        workload_id=f"worker-{dep_name}",
                        workload_type="gke_worker",
                        name=dep_name,
                        status=dep_status,
                        created_at=created_at,
                        replicas=dep_replicas,
                        image=dep_image,
                        namespace=namespace,
                        worker_type="deployment",
                        service_uris=service_uris,
                    )
                    workers.append(workload)
                if workers:
                    logger.info(
                        f"[{organization_id}] Found {len(workers)} workload(s) via K8s API fallback in namespace {namespace}"
                    )
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"[{organization_id}] K8s fallback query failed: {e}")
            except Exception as e:
                logger.warning(f"[{organization_id}] K8s fallback query failed: {e}")

        return workers
    except Exception as e:
        logger.error(f"[{organization_id}] Failed to list gke_workers: {e}", exc_info=True)
        return []


def _list_akash_deployments(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    status_filter: Optional[str],
    akt_usd_rate: float,
) -> List[UnifiedWorkloadSummary]:
    """List Akash deployments from Firestore. Sync — the caller pre-fetches the
    AKT/USD rate and offloads this via asyncio.to_thread (the function body is pure
    sync Firestore I/O)."""
    try:
        db = firestore.Client()

        # Query akash_deployments collection
        query = (
            db.collection("akash_deployments")
            .where("organization_id", "==", organization_id)
            .where("cluster_id", "==", cluster_id)
        )

        if status_filter:
            query = query.where("status", "==", status_filter)

        # akt_usd_rate pre-fetched by the caller (cached, 1-hour TTL).

        # Platform fee: $0.002 per vCPU per hour, 730 hours/month
        logger.debug(f"[{organization_id}] Querying akash_deployments: cluster={cluster_id}, status={status_filter}")
        deployments = []
        for doc in query.stream():
            data = doc.to_dict()

            deployment_id = data.get("deployment_id") or doc.id

            # Convert lease price to USD (denom-aware: uakt uses AKT rate, uact is already USD)
            price_uakt = data.get("price_per_month_uakt")
            price_denom = data.get("price_denom", "uakt")  # Legacy deployments default to uakt
            if price_uakt:
                if price_denom == "uact":
                    price_usd = round(price_uakt / 1_000_000, 2)  # ACT = $1 USD
                else:
                    price_usd = round(price_uakt / 1_000_000 * akt_usd_rate, 2)  # AKT × rate
            else:
                price_usd = None

            # Platform fee based on CPU units
            resources = data.get("resources") or {}
            cpu_units = resources.get("cpu_units") or resources.get("cpu", 0)
            platform_fee = round(cpu_units * PLATFORM_FEE_PER_VCPU_HOUR * HOURS_PER_MONTH, 2)

            # Total = lease + platform fee
            total_cost = round((price_usd or 0) + platform_fee, 2) if price_usd is not None else None

            # Accrued cost: pro-rated from created_at to now
            accrued_cost = None
            created_at = data.get("created_at")
            if total_cost is not None and created_at is not None:
                if isinstance(created_at, datetime):
                    created_dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
                else:
                    try:
                        created_dt = datetime.fromisoformat(str(created_at)).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        created_dt = None

                if created_dt is not None:
                    elapsed_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
                    hourly_rate = total_cost / HOURS_PER_MONTH
                    accrued_cost = hourly_rate * elapsed_hours

            # Derive workload_type from region_id: dfc-* regions → dfc_deployment
            region_id = data.get("region_id", "")
            wl_type = "dfc_deployment" if region_id.startswith("dfc-") else "akash_deployment"

            provider = _resolve_provider(data)

            workload = UnifiedWorkloadSummary(
                workload_id=f"akash-{deployment_id}",
                workload_type=wl_type,
                name=data.get("worker_id") or deployment_id,
                status=data.get("status", "unknown"),
                created_at=created_at,
                replicas=data.get("worker_count"),
                image=data.get("app_image"),
                namespace=data.get("namespace"),
                provider=provider,
                provider_address=data.get("provider_address"),
                region_id=region_id,
                dseq=deployment_id,
                service_uris=data.get("service_uris") or [],
                price_per_month_uakt=price_uakt,
                price_per_month_usd=price_usd,
                platform_fee_usd=platform_fee,
                total_cost_usd=total_cost,
                akt_usd_rate=akt_usd_rate,
                accrued_cost_usd=accrued_cost,
                resources=resources,
                # pods_ready/pods_ready_at: written by /pods endpoint on first
                # observed pod readiness. Distinguishes "lease formed" from
                # "pods actually serving" — see fix(api): pods_ready field.
                pods_ready=bool(data.get("pods_ready", False)),
                pods_ready_at=data.get("pods_ready_at"),
            )
            deployments.append(workload)

        logger.debug(f"[{organization_id}] Found {len(deployments)} akash_deployments for cluster={cluster_id}")
        return deployments
    except Exception as e:
        logger.error(f"[{organization_id}] Failed to list akash_deployments: {e}", exc_info=True)
        return []


def _list_cronjobs(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    status_filter: Optional[str],
) -> List[UnifiedWorkloadSummary]:
    """List CronJobs from Firestore"""
    try:
        db = firestore.Client()

        # Query cronjobs collection
        query = db.collection("cronjobs").where("organization_id", "==", organization_id).where("cluster_id", "==", cluster_id)

        if status_filter:
            query = query.where("status", "==", status_filter)

        cronjobs = []
        for doc in query.stream():
            data = doc.to_dict()

            cronjob_name = data.get("name") or doc.id
            workload = UnifiedWorkloadSummary(
                workload_id=f"cron-{cronjob_name}",
                workload_type="cronjob",
                name=cronjob_name,
                status=data.get("status", "unknown"),
                created_at=data.get("created_at"),
                replicas=1,  # CronJobs always have 1 replica
                image=data.get("image"),
                namespace=data.get("namespace"),
                schedule=data.get("schedule"),
                last_run=data.get("last_run"),
            )
            cronjobs.append(workload)

        return cronjobs
    except Exception as e:
        logger.error(f"[{organization_id}] Failed to list cronjobs: {e}", exc_info=True)
        return []


def _list_lat_deployments(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    status_filter: Optional[str],
) -> List[UnifiedWorkloadSummary]:
    """List LAT (Latitude.sh) workloads for a cluster.

    Unlike Akash/GKE, LAT VMs aren't tracked in their own Firestore collection
    — the VM/server identity lives in cluster metadata persisted by the
    Latitude provisioning path (see handlers/clusters.py provider_kind="latitude").

    Returns at most one workload per cluster: the canonical Latitude
    resource recorded in cluster metadata. Status is inferred from
    metadata presence (cluster has a VM/server id ⇒ "active") — call
    /pods to get the live Latitude API status.
    """
    try:
        from services.entity_store_factory import get_entity_store

        registry = get_entity_store()
        cluster_data = registry.get_cluster(organization_id, project_id, cluster_id)
        if cluster_data is None:
            return []

        metadata = cluster_data.get("metadata") or {}
        if metadata.get("provider_kind") != "latitude":
            return []

        vm_id = str(metadata.get("latitude_vm_id") or "").strip()
        server_id = str(metadata.get("latitude_server_id") or "").strip()
        target = vm_id or server_id
        if not target:
            return []

        name = (
            metadata.get("latitude_vm_name")
            or metadata.get("latitude_server_hostname")
            or metadata.get("latitude_server_name")
            or target
        )
        plan_id = metadata.get("latitude_plan_id")
        synthesized_status = "active"
        if status_filter and status_filter != synthesized_status:
            return []

        return [
            UnifiedWorkloadSummary(
                workload_id=f"lat-{target}",
                workload_type="lat_deployment",
                name=name,
                status=synthesized_status,
                created_at=cluster_data.get("created_at"),
                replicas=1,
                image=metadata.get("latitude_image"),
                namespace=cluster_data.get("namespace"),
                provider="lat",
                latitude_resource_kind=metadata.get("latitude_resource_kind") or ("vm" if vm_id else "server"),
                latitude_plan_id=plan_id,
            )
        ]
    except Exception as e:
        logger.error(f"[{organization_id}] Failed to list LAT deployments: {e}", exc_info=True)
        return []


# =============================================================================
# Get Workload (Unified Describe)
# =============================================================================


@workloads_router.get(
    "/{workload_id}",
    summary="Get workload details",
    description="""
Get detailed information about a specific workload.

Automatically routes to the correct platform based on workload ID prefix:
- `worker-{id}` → GKE worker
- `akash-{dseq}` → Akash deployment
- `cron-{name}` → CronJob

**Response:**
Comprehensive workload details including configuration, status, health, and metrics.
""",
)
async def get_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    organization: Dict = Depends(get_current_organization),
):
    """
    Get detailed information about a specific workload.

    Routes to platform-specific implementation based on workload_id prefix.
    """
    logger.info(f"[{organization_id}] Getting workload: {workload_id}")

    # Parse workload type
    workload_type, resource_id = _parse_workload_id(workload_id)

    # Route to platform-specific handler
    if workload_type == "gke_worker":
        detail = await _get_gke_worker_detail(organization_id, cluster_id, resource_id)
    elif workload_type == "akash_deployment":
        detail = await _get_akash_deployment_detail(organization_id, cluster_id, resource_id)
    elif workload_type == "lat_deployment":
        detail = await _get_lat_deployment_detail(organization_id, project_id, cluster_id, resource_id)
    elif workload_type == "cronjob":
        detail = await _get_cronjob_detail(organization_id, cluster_id, resource_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")

    if not detail:
        raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found")

    return detail.to_dict()


async def _get_gke_worker_detail(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
) -> Optional[UnifiedWorkloadDetail]:
    """Get GKE worker details from Firestore and Kubernetes"""
    db = await _get_firestore_client(firestore)

    # Query Firestore for worker metadata (workers collection, then gke_deployments fallback)
    query = (
        db.collection("workers")
        .where("organization_id", "==", organization_id)
        .where("cluster_id", "==", cluster_id)
        .where("worker_id", "==", worker_id)
        .limit(1)
    )
    docs = list(query.stream())
    if not docs:
        # Fallback: gke_deployments collection (written by _track_gke_deployment)
        gke_query = (
            db.collection("gke_deployments")
            .where("organization_id", "==", organization_id)
            .where("cluster_id", "==", cluster_id)
            .where("worker_id", "==", worker_id)
            .limit(1)
        )
        gke_docs = list(gke_query.stream())
        if not gke_docs:
            return None
        docs = gke_docs

    data = docs[0].to_dict()
    namespace = data.get("namespace", f"c-{cluster_id}")

    # Get endpoints from Firestore or query K8s Service
    endpoints = data.get("service_uris") or data.get("endpoints", [])

    # Try to query K8s Service for ClusterIP
    try:
        v1 = k8s_client.CoreV1Api()
        svc = v1.read_namespaced_service(name=f"worker-{worker_id}", namespace=namespace)
        if svc.spec.cluster_ip:
            # Build endpoints from ClusterIP and ports
            cluster_endpoints = []
            if svc.spec.ports:
                for port in svc.spec.ports:
                    cluster_endpoints.append(f"{svc.spec.cluster_ip}:{port.port}")
            if cluster_endpoints:
                endpoints = cluster_endpoints
    except ApiException as e:
        if e.status == 404:
            # Service doesn't exist, use Firestore endpoints (graceful fallback)
            logger.debug(f"Service worker-{worker_id} not found in {namespace}, using Firestore endpoints")
        else:
            # Log other K8s API errors but don't fail
            logger.warning(f"Failed to query K8s Service: {e.reason}")

    # Build unified detail
    detail = UnifiedWorkloadDetail(
        workload_id=f"worker-{worker_id}",
        workload_type="gke_worker",
        name=data.get("name") or worker_id,
        status=data.get("status", "unknown"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        namespace=namespace,
        replicas=data.get("replicas"),
        image=data.get("image"),
        resources=data.get("resources", {}),
        env_vars=data.get("env_vars", {}),
        labels=data.get("labels", {}),
        health_status=data.get("health_status"),
        endpoints=endpoints,
        # Platform-specific fields
        deployment_name=f"worker-{worker_id}",
        worker_type=data.get("worker_type"),
        autoscaling=data.get("autoscaling"),
        volumes=data.get("volumes", []),
    )

    return detail


async def _get_akash_deployment_detail(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
) -> Optional[UnifiedWorkloadDetail]:
    """Get Akash deployment details from Firestore"""
    db = await _get_firestore_client(firestore)

    # Query Firestore
    doc = db.collection("akash_deployments").document(deployment_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()

    # Verify ownership
    if data.get("organization_id") != organization_id:
        return None
    if data.get("cluster_id") != cluster_id:
        return None

    # Get endpoints from Firestore, or query lease-status if empty
    endpoints = data.get("service_uris", [])
    provider_uri = data.get("provider_uri")

    # If service_uris is empty, try to query lease-status
    if not endpoints and data.get("provider_address"):
        try:
            keyring_backend = os.environ.get("AKASH_KEYRING_BACKEND", "test")
            rpc_node = os.environ.get("AKASH_RPC_NODE") or os.environ.get("AKASH_NODE", "https://rpc.akashnet.net:443")

            cmd = [
                "provider-services",
                "lease-status",
                f"--dseq={deployment_id}",
                f"--provider={data.get('provider_address')}",
                "--from",
                "default",
                f"--keyring-backend={keyring_backend}",
                f"--node={rpc_node}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                status_data = json.loads(result.stdout)
                endpoints = status_data.get("result", {}).get("endpoint", [])
        except Exception as e:
            # Log error but don't fail - use Firestore endpoints (graceful fallback)
            logger.debug(f"Failed to query lease-status for {deployment_id}: {str(e)}")

    # Build unified detail
    detail = UnifiedWorkloadDetail(
        workload_id=f"akash-{deployment_id}",
        workload_type="akash_deployment",
        name=data.get("worker_id") or deployment_id,
        status=data.get("status", "unknown"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        namespace=data.get("namespace"),
        replicas=data.get("worker_count"),
        image=data.get("app_image"),
        resources=data.get("resources", {}),
        env_vars=data.get("environment_variables", {}),
        labels={},  # Akash doesn't have labels
        health_status=None,  # TODO: Check provider health
        endpoints=endpoints,
        # Platform-specific fields
        dseq=deployment_id,
        provider_address=data.get("provider_address"),
        provider_uri=provider_uri,
        consul_registered=data.get("consul_registered"),
        lease_status=data.get("lease_status"),
    )

    return detail


async def _get_lat_deployment_detail(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
) -> Optional[UnifiedWorkloadDetail]:
    """Get LAT (Latitude) deployment detail by querying the live Latitude API.

    Composes cluster metadata (provider_kind, latitude_vm_id, plan) with the
    Latitude SDK's get_vm_status response (live status, IP) into a unified
    detail view consistent with the GKE/Akash detail handlers.
    """
    try:
        from services.entity_store_factory import get_entity_store

        registry = get_entity_store()
        cluster_data = registry.get_cluster(organization_id, project_id, cluster_id)
        if cluster_data is None:
            return None

        metadata = cluster_data.get("metadata") or {}
        if metadata.get("provider_kind") != "latitude":
            return None

        expected_vm = str(metadata.get("latitude_vm_id") or "").strip()
        expected_server = str(metadata.get("latitude_server_id") or "").strip()
        is_vm = bool(expected_vm) and expected_vm == resource_id
        is_server = bool(expected_server) and expected_server == resource_id
        if not is_vm and not is_server:
            return None

        # Live status query — best-effort. If Latitude is unreachable, return
        # the cluster-metadata view rather than 502'ing the whole detail call.
        ip = None
        status = "unknown"
        try:
            from latitude_client import LatitudeClient

            client = LatitudeClient()
            if is_vm:
                vm = client.get_vm_status(resource_id)
                status = (vm.status or "unknown").lower()
                ip = vm.ip
                name = vm.name or resource_id
            else:
                server = client.get_server_status(resource_id)
                status = (server.status or "unknown").lower()
                ip = getattr(server, "ip", None) or getattr(server, "primary_ipv4", None)
                name = getattr(server, "name", None) or resource_id
        except Exception as exc:
            logger.warning("Latitude detail lookup failed for resource=%s: %s", resource_id, exc)
            name = metadata.get("latitude_vm_name") or metadata.get("latitude_server_name") or resource_id

        return UnifiedWorkloadDetail(
            workload_id=f"lat-{resource_id}",
            workload_type="lat_deployment",
            name=name,
            status=status,
            created_at=cluster_data.get("created_at"),
            namespace=cluster_data.get("namespace"),
            replicas=1,
            resources={"latitude_plan_id": metadata.get("latitude_plan_id")},
            endpoints=[ip] if ip else [],
            health_status=status,
        )
    except Exception as exc:
        logger.error(
            "[%s] Failed to get LAT deployment detail: %s",
            organization_id,
            exc,
            exc_info=True,
        )
        return None


async def _delete_lat_deployment(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
) -> Dict[str, Any]:
    """Delete a LAT (Latitude) VM/server.

    Delegates to latitude_client.destroy_vm or destroy_server based on the
    cluster's recorded resource kind. Doesn't touch cluster metadata —
    callers that want the cluster record cleaned up should use the
    cluster-delete path which calls destroy_latitude_servers_for_cluster.
    """
    from services.entity_store_factory import get_entity_store

    registry = get_entity_store()
    cluster_data = registry.get_cluster(organization_id, project_id, cluster_id)
    if cluster_data is None:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

    metadata = cluster_data.get("metadata") or {}
    if metadata.get("provider_kind") != "latitude":
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} is not a Latitude cluster")

    expected_vm = str(metadata.get("latitude_vm_id") or "").strip()
    expected_server = str(metadata.get("latitude_server_id") or "").strip()
    is_vm = bool(expected_vm) and expected_vm == resource_id
    is_server = bool(expected_server) and expected_server == resource_id
    if not is_vm and not is_server:
        raise HTTPException(
            status_code=404,
            detail=f"Resource {resource_id} not registered on cluster {cluster_id}",
        )

    try:
        from latitude_client import LatitudeClient

        client = LatitudeClient()
        if is_vm:
            client.destroy_vm(resource_id)
            kind = "vm"
        else:
            client.destroy_server(resource_id)
            kind = "server"
    except Exception as exc:
        logger.warning("Latitude destroy failed for resource=%s: %s", resource_id, exc)
        raise HTTPException(status_code=502, detail=f"Latitude destroy failed: {exc}")

    return {
        "workload_id": f"lat-{resource_id}",
        "status": "deleted",
        "kind": kind,
    }


async def _get_cronjob_detail(
    organization_id: str,
    cluster_id: str,
    cronjob_name: str,
) -> Optional[UnifiedWorkloadDetail]:
    """Get CronJob details from Firestore"""
    db = await _get_firestore_client(firestore)

    # Query Firestore
    query = (
        db.collection("cronjobs")
        .where("organization_id", "==", organization_id)
        .where("cluster_id", "==", cluster_id)
        .where("name", "==", cronjob_name)
        .limit(1)
    )

    docs = list(query.stream())
    if not docs:
        return None

    data = docs[0].to_dict()

    # Build unified detail
    detail = UnifiedWorkloadDetail(
        workload_id=f"cron-{cronjob_name}",
        workload_type="cronjob",
        name=cronjob_name,
        status=data.get("status", "unknown"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        namespace=data.get("namespace"),
        replicas=1,
        image=data.get("image"),
        resources=data.get("resources", {}),
        env_vars=data.get("env_vars", {}),
        labels=data.get("labels", {}),
        health_status=None,  # CronJobs don't have health checks
        endpoints=[],  # CronJobs don't expose endpoints
        # Platform-specific fields
        schedule=data.get("schedule"),
        last_run=data.get("last_run"),
        next_run=data.get("next_run"),
        successful_jobs=data.get("successful_jobs", 0),
        failed_jobs=data.get("failed_jobs", 0),
    )

    return detail


# =============================================================================
# Delete Workload (Unified)
# =============================================================================


@workloads_router.delete(
    "/{workload_id}",
    summary="Delete workload",
    description="""
Delete a workload.

Automatically routes to the correct platform based on workload ID prefix.

**Behavior:**
- GKE worker: Deletes Kubernetes deployment and service
- Akash deployment: Closes deployment and lease
- CronJob: Deletes Kubernetes CronJob

**Response:**
202 Accepted with deletion operation ID.
""",
)
async def delete_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    organization: Dict = Depends(get_current_organization),
):
    """
    Delete a workload.

    Routes to platform-specific delete implementation.
    """
    logger.info(f"[{organization_id}] Deleting workload: {workload_id}")

    # Parse workload type
    workload_type, resource_id = _parse_workload_id(workload_id)

    # Route to platform-specific handler
    if workload_type == "gke_worker":
        result = await _delete_gke_worker(organization_id, cluster_id, resource_id)
    elif workload_type == "akash_deployment":
        result = await _delete_akash_deployment(organization_id, cluster_id, resource_id)
    elif workload_type == "lat_deployment":
        result = await _delete_lat_deployment(organization_id, project_id, cluster_id, resource_id)
    elif workload_type == "cronjob":
        result = await _delete_cronjob(organization_id, cluster_id, resource_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")

    return result


async def _delete_gke_worker(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
) -> Dict[str, Any]:
    """Delete GKE worker"""
    # TODO: Implement GKE worker deletion
    # This should call existing workers.py delete_worker endpoint

    # Call existing implementation
    # For now, return placeholder
    return {
        "workload_id": f"worker-{worker_id}",
        "status": "deleting",
        "message": "GKE worker deletion initiated",
    }


async def _delete_akash_deployment(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
) -> Dict[str, Any]:
    """Delete Akash deployment"""

    # Verify ownership before closing the lease. deployment_id (dseq) is caller-supplied via
    # the {workload_id} path segment; without this check a caller scoped to their own cluster
    # could close (terminate the lease + stop billing on) ANOTHER tenant's Akash deployment by
    # naming its dseq. Every sibling Akash handler (_kill/_exec/_logs/events/pods) does this;
    # delete previously omitted it (cross-org IDOR). 404 (not 403) mirrors the siblings so a
    # foreign dseq's existence is not disclosed. [[control-plane hardening — task #56]]
    db = await _get_firestore_client(firestore)
    doc = db.collection("akash_deployments").document(deployment_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")
    data = doc.to_dict()
    if data.get("organization_id") != organization_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")
    if data.get("cluster_id") != cluster_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    # Task #61: close via the honest _close_deployment_with_audit path — it reaches BOTH
    # backends (self-managed re-auth as the paying wallet + console fallback) and writes the
    # tracking doc to status=closed on success / close_failed on failure. The old code closed
    # via the self-managed AkashClient and NEVER updated Firestore, so a user-closed console
    # deploy either couldn't be closed at all, or stayed status=active and was later re-closed
    # by the stale sweeper — mislabelling an already-closed deployment close_failed and skewing
    # the close-failure metric. [[task #61 — quorum finding]]
    from handlers.akash import _close_deployment_with_audit

    try:
        await _close_deployment_with_audit(
            deployment_id,
            caller="delete-workload",
            reason=f"user delete workload akash-{deployment_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to close Akash deployment") from e

    return {
        "workload_id": f"akash-{deployment_id}",
        "status": "closed",
        "message": "Akash deployment closed successfully",
    }


async def _delete_cronjob(
    organization_id: str,
    cluster_id: str,
    cronjob_name: str,
) -> Dict[str, Any]:
    """Delete CronJob"""
    # TODO: Implement CronJob deletion
    # This should call existing blazing_cron.py delete endpoint
    return {
        "workload_id": f"cron-{cronjob_name}",
        "status": "deleting",
        "message": "CronJob deletion initiated",
    }


# =============================================================================
# Get Workload Events (Unified)
# =============================================================================


@workloads_router.get(
    "/{workload_id}/events",
    summary="Get workload events",
    description="""
Get lifecycle events for a workload (audit trail, status changes, errors).

Automatically routes to the correct platform based on workload ID prefix.

**Response:**
Chronological list of events (newest first).
""",
)
async def get_workload_events(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    limit: int = Query(100, ge=1, le=1000),
    organization: Dict = Depends(get_current_organization),
):
    """
    Get workload lifecycle events.

    Routes to platform-specific events implementation.
    """
    logger.info(f"[{organization_id}] Getting events for workload: {workload_id}")

    # Parse workload type
    workload_type, resource_id = _parse_workload_id(workload_id)

    # Route to platform-specific handler
    if workload_type == "gke_worker":
        events = await _get_gke_worker_events(organization_id, cluster_id, resource_id, limit)
    elif workload_type == "akash_deployment":
        events = await _get_akash_deployment_events(organization_id, cluster_id, resource_id, limit)
    elif workload_type == "lat_deployment":
        # LAT has no per-VM events backend yet. Return an empty list rather
        # than 400/501 so cross-platform callers can iterate workloads
        # without special-casing LAT.
        events = []
    elif workload_type == "cronjob":
        events = await _get_cronjob_events(organization_id, cluster_id, resource_id, limit)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")

    return {
        "workload_id": workload_id,
        "events": [e.to_dict() for e in events],
        "total": len(events),
    }


async def _get_gke_worker_events(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
    limit: int,
) -> List[UnifiedWorkloadEvent]:
    """Get GKE worker events from Kubernetes"""
    # TODO: Query Kubernetes events API
    # kubectl get events --namespace={namespace} --field-selector involvedObject.name=worker-{id}
    return []


async def _get_akash_deployment_events(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
    limit: int,
) -> List[UnifiedWorkloadEvent]:
    """Get Akash deployment events from Firestore audit log"""
    db = await _get_firestore_client(firestore)

    # Query audit log
    query = (
        db.collection("akash_events")
        .where("deployment_id", "==", deployment_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )

    events = []
    for doc in query.stream():
        data = doc.to_dict()

        # Validate ownership
        if data.get("organization_id") != organization_id:
            continue
        if data.get("cluster_id") != cluster_id:
            continue

        event = UnifiedWorkloadEvent(
            event_id=doc.id,
            workload_id=f"akash-{deployment_id}",
            timestamp=data.get("timestamp", datetime.utcnow()),
            event_type=data.get("event_type", "unknown"),
            message=data.get("message", ""),
            severity=data.get("severity", "info"),
        )
        events.append(event)

    return events


async def _get_cronjob_events(
    organization_id: str,
    cluster_id: str,
    cronjob_name: str,
    limit: int,
) -> List[UnifiedWorkloadEvent]:
    """Get CronJob events from Firestore"""
    db = await _get_firestore_client(firestore)

    # Query job execution history
    query = (
        db.collection("cronjob_executions")
        .where("cronjob_name", "==", cronjob_name)
        .order_by("started_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )

    events = []
    for doc in query.stream():
        data = doc.to_dict()

        event = UnifiedWorkloadEvent(
            event_id=doc.id,
            workload_id=f"cron-{cronjob_name}",
            timestamp=data.get("started_at", datetime.utcnow()),
            event_type="execution",
            message=f"Job completed with status: {data.get('status', 'unknown')}",
            severity="info" if data.get("status") == "success" else "warning",
            exit_code=data.get("exit_code"),
            duration_seconds=data.get("duration_seconds"),
        )
        events.append(event)

    return events


# =============================================================================
# Pod Status (Unified)
# =============================================================================


class PodStatus(BaseModel):
    """Pod status information for a workload."""

    name: str = Field(..., description="Pod name")
    phase: str = Field(..., description="Pod phase (Running, Pending, Failed, etc.)")
    ready: bool = Field(..., description="Whether the pod is ready to serve traffic")
    restart_count: int = Field(..., description="Total number of container restarts")
    started_at: Optional[str] = Field(None, description="Pod start time in ISO 8601 format")
    waiting_reason: Optional[str] = Field(
        None,
        description="Container waiting reason if not running (e.g. ImagePullBackOff, CrashLoopBackOff)",
    )
    scheduled: Optional[bool] = Field(
        None,
        description="Whether the scheduler has placed this pod on a node (PodScheduled condition)",
    )
    scheduling_reason: Optional[str] = Field(
        None,
        description=(
            "Why the pod is not scheduled, straight from the PodScheduled condition "
            "(e.g. Unschedulable: 0/3 nodes are available: insufficient cpu). Populated "
            "only when scheduling has NOT succeeded."
        ),
    )


@workloads_router.get(
    "/{workload_id}/pods",
    summary="List workload pods",
    description="""
List all pods for a workload across GKE, Akash, and CronJob platforms.

**GKE:** Returns pods from the Kubernetes worker's StatefulSet, including container status.

**Akash/DFC:** Returns service replicas from lease-status, one replica per pod.

**CronJob:** Returns 400 (not applicable).

Allows E2E tests to poll pod readiness and discover when deployments are healthy.
""",
)
async def list_workload_pods(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    organization: Dict = Depends(get_current_organization),
) -> Dict[str, List[PodStatus]]:
    """List all pods for a workload."""
    workload_type, resource_id = _parse_workload_id(workload_id)

    if workload_type == "gke_worker":
        pods = await _list_gke_pods(organization_id, cluster_id, resource_id)
    elif workload_type == "akash_deployment":
        pods = await _list_akash_pods(organization_id, cluster_id, resource_id)
    elif workload_type == "lat_deployment":
        pods = await _list_lat_pods(organization_id, project_id, cluster_id, resource_id)
    elif workload_type == "cronjob":
        raise HTTPException(
            status_code=400,
            detail="Pod status is not applicable to CronJob workloads",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")

    return {"pods": pods}


def _resolve_gke_worker(
    db: Any,
    organization_id: str,
    cluster_id: str,
    worker_id: str,
) -> Dict[str, Any]:
    """Resolve GKE worker metadata from Firestore.

    Checks ``gke_deployments`` first (canonical). Falls back to ``workers``
    (legacy, for pre-unification deploys). Raises HTTP 404 only if neither
    collection has a record.

    Returns a dict with at least ``namespace`` and ``worker_id`` keys.
    """
    # Primary: gke_deployments collection (canonical source)
    gke_query = (
        db.collection("gke_deployments")
        .where("organization_id", "==", organization_id)
        .where("cluster_id", "==", cluster_id)
        .where("worker_id", "==", worker_id)
        .limit(1)
    )
    gke_docs = list(gke_query.stream())
    if gke_docs:
        return gke_docs[0].to_dict()

    # Legacy fallback: workers collection (for pre-unification deploys)
    query = (
        db.collection("workers")
        .where("organization_id", "==", organization_id)
        .where("cluster_id", "==", cluster_id)
        .where("worker_id", "==", worker_id)
        .limit(1)
    )
    docs = list(query.stream())
    if docs:
        return docs[0].to_dict()

    # Debug: list all gke_deployments for this cluster to diagnose field mismatches
    debug_docs = list(
        db.collection("gke_deployments")
        .where("organization_id", "==", organization_id)
        .where("cluster_id", "==", cluster_id)
        .limit(5)
        .stream()
    )
    if debug_docs:
        stored_workers = [(d.id, d.to_dict().get("worker_id")) for d in debug_docs]
        logger.warning(
            f"_resolve_gke_worker 404: worker_id={worker_id!r} not found, "
            f"but cluster has {len(debug_docs)} doc(s): {stored_workers}"
        )
    else:
        logger.warning(f"_resolve_gke_worker 404: no gke_deployments for org={organization_id}, cluster={cluster_id}")

    raise HTTPException(status_code=404, detail=f"Workload worker-{worker_id} not found")


async def _list_gke_pods(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
) -> List[PodStatus]:
    """List pods for a GKE worker via Kubernetes API."""
    db = await _get_firestore_client(firestore)

    # Look up worker in Firestore (gke_deployments first, workers legacy fallback)
    data = _resolve_gke_worker(db, organization_id, cluster_id, worker_id)
    namespace = data.get("namespace", f"c-{cluster_id}")
    worker_id_from_doc = data.get("worker_id", worker_id)

    try:
        v1 = k8s_client.CoreV1Api()
        pod_list = v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"worker-id={worker_id_from_doc}",
        )
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Namespace {namespace} not found")
        raise HTTPException(status_code=e.status or 500, detail=f"K8s API error: {e.reason}")

    pods = []
    for pod in pod_list.items:
        # Check if pod is ready
        container_statuses = pod.status.container_statuses or []
        # `all([])` is True, so a pod with NO container statuses — exactly what a
        # Pending pod awaiting scheduling looks like — reported ready=True. That is a
        # false-green generator: any caller polling readiness concludes the workload is
        # serving while nothing has started. OBSERVED 2026-08-01 (run 30698461383,
        # C0-gcp): "FINAL STATE: worker-tetris-... phase=Pending ready=True reason=None"
        # — a self-contradictory status the API itself emitted. A pod with no containers
        # is by definition not ready.
        ready = bool(container_statuses) and all(c.ready for c in container_statuses)
        restart_count = sum(c.restart_count for c in container_statuses)

        started_at = None
        if pod.status.start_time:
            started_at = pod.status.start_time.isoformat()

        # Extract waiting reason from first non-running container (if any)
        waiting_reason = None
        for cs in container_statuses:
            if cs.state and cs.state.waiting and cs.state.waiting.reason:
                waiting_reason = cs.state.waiting.reason
                break

        # Why is it Pending? `waiting_reason` above comes from CONTAINER statuses, and an
        # UNSCHEDULED pod has none — so a pod the scheduler could not place reported
        # phase=Pending with waiting_reason=None: no diagnostic information at all. Every
        # such CI failure therefore ends in a guess ("No waiting reason — likely node
        # scheduling delay (autoscaler?)"). The answer is in the PodScheduled condition,
        # which Kubernetes populates with the real cause, e.g.
        #   Unschedulable: 0/3 nodes are available: 3 Insufficient cpu
        # MEASURED 2026-08-01: C2 (run 30698461383 and others) skipped 900s on
        # "GCP primary pod never scheduled", and C0-gcp failed the same way, with the
        # cause never surfaced. cluster_metrics.py:1077 already reads this condition;
        # this is the workloads path catching up.
        scheduled = None
        scheduling_reason = None
        for cond in pod.status.conditions or []:
            if cond.type != "PodScheduled":
                continue
            scheduled = cond.status == "True"
            if not scheduled:
                scheduling_reason = ": ".join(p for p in (cond.reason, cond.message) if p) or None
            break

        pods.append(
            PodStatus(
                name=pod.metadata.name,
                phase=pod.status.phase,
                ready=ready,
                restart_count=restart_count,
                started_at=started_at,
                waiting_reason=waiting_reason,
                scheduled=scheduled,
                scheduling_reason=scheduling_reason,
            )
        )

    return pods


# Console-API deployment statuses that mean the workload is up and serving.
_AKASH_CONSOLE_RUNNING_STATUSES = {"active"}
# Statuses that mean the deployment failed and will not become ready.
_AKASH_CONSOLE_FAILED_STATUSES = {"failed", "unhealthy", "secrets_injection_failed"}


def _recorded_closed(data: dict) -> bool:
    """Does this deployment's OWN Firestore record say the lease was closed?

    A CORROBORATING signal only — never a standalone one. `status="closed"` is written by
    several paths that never confirmed an on-chain close, and the worst of them matches the
    exact population this is used for: admin/wallet_pool.py:1183 SKIPS the close entirely
    when `wallet_key` is falsy and then stamps "closed" anyway, and on an exception logs
    "will mark closed anyway" and proceeds. services/akash_client.py maps the stderr
    substring "key not found" to already-closed — which is this file's own documented
    signature (see the Console-owned note below) for querying a Console-owned lease with a
    local keyring identity. So a document can read "closed" while the lease is live and
    burning escrow.

    Treating this field as proof would return an empty pod list for a running workload, and
    nothing downstream would catch it: the stale sweepers filter status=="active" and the
    reconciler skips CLOSED. It is therefore only ever used to confirm what the LIVE sources
    (Console, then the provider) have already independently reported as gone.

    `str(... or "").strip().lower()` because Firestore is schema-less with many writers here:
    a bare `.lower()` raises AttributeError on a non-str enum and 500s every call including
    live ones, and an unstripped compare lets " closed " miss and fall into the cascade.
    Mirrors the defensive form already used on the Console response in _list_akash_pods.
    """
    return str(data.get("status") or "").strip().lower() == AkashDeploymentStatus.CLOSED.value


# How many times to sweep ALL Console accounts before giving up, and the pause
# between sweeps. Bounded deliberately: this sits inside a request handler that the
# E2E polls, so the budget must stay well under the caller's own interval.
_CONSOLE_STATUS_SWEEPS = 3
_CONSOLE_STATUS_RETRY_SEC = 2.0


async def _lease_status_pods_from_provider(deployment_id: str, data: dict, keys: List[str]) -> Optional[List[PodStatus]]:
    """PodStatus from the provider's own lease status, or None if that is not possible.

    The provider is authoritative about its leases and answers with the real per-service
    replica tally, so this reports MEASURED counts rather than fanning one
    deployment-level status across an expected replica count.

    Returns None — never raises — when the provider cannot be reached or identified, so
    the caller falls back to the existing error path with its existing diagnosis.
    """
    from services.console_api_backend import ConsoleApiBackend  # noqa: PLC0415

    provider_address = data.get("provider_address")
    if not provider_address:
        return None

    try:
        from services.cosmos_rest_client import CosmosRestClient  # noqa: PLC0415

        # The provider's host is on-chain and needs no auth — the right source here,
        # because the Console deployment object (which carries service_uris) is exactly
        # what is missing when this path is reached.
        async with CosmosRestClient() as chain:
            provider_uri = await chain.resolve_provider_uri(provider_address)
    except Exception as exc:  # noqa: BLE001 — a chain lookup failure is not fatal here
        logger.warning("provider_uri lookup failed for %s (dseq=%s): %s", provider_address, deployment_id, exc)
        return None
    if not provider_uri:
        # Say so. A silent None here is how this fallback looked "not wired" in run
        # 31398478992 while it was in fact running and giving up — the chain lookup was
        # querying a retired module version and failing open.
        logger.warning(
            "dseq=%s: cannot reach the provider fallback — no host_uri for %s",
            deployment_id,
            provider_address,
        )
        return None

    last_err: Optional[Exception] = None
    for key in keys:
        try:
            status = await ConsoleApiBackend(api_key=key).lease_status_from_provider(
                deployment_id, provider_address=provider_address, provider_uri=provider_uri
            )
        except Exception as exc:  # noqa: BLE001 — try the next account
            last_err = exc
            continue
        services = (status or {}).get("services") or {}
        pods: List[PodStatus] = []
        for svc_name, svc in services.items():
            if not isinstance(svc, dict):
                continue
            total = int(svc.get("total") or svc.get("replicas") or 0)
            ready = int(svc.get("ready_replicas") or svc.get("available") or 0)
            for i in range(max(total, ready)):
                pods.append(
                    PodStatus(
                        name=f"{svc_name}-{i}" if max(total, ready) > 1 else str(svc_name),
                        phase="Running" if i < ready else "Pending",
                        ready=i < ready,
                        restart_count=0,
                        started_at=None,
                        waiting_reason=None if i < ready else f"provider_status ready={ready}/{total}",
                    )
                )
        logger.info(
            "dseq=%s: Console index was blind; provider %s reported %d pod(s) via scoped JWT",
            deployment_id,
            provider_address,
            len(pods),
        )
        return pods
    logger.warning("Provider lease-status also failed for dseq=%s: %s", deployment_id, last_err)
    return None


async def _list_akash_pods_via_console(deployment_id: str, data: dict) -> List[PodStatus]:
    """List pods for a Console-API Akash deployment.

    Console-created deployments hold their wallet server-side, so the API
    server has no local keyring identity for them — `provider-services
    lease-status` (which needs `--from <key>`) cannot query them and fails
    with "default.info: key not found". The Console API exposes deployment
    status directly instead. It does not break status down per replica, so a
    single PodStatus is synthesised from the deployment-level status.
    """
    from services.console_api_backend import ConsoleApiBackend

    from services.console_keys import console_api_keys  # noqa: PLC0415

    keys = console_api_keys()
    if not keys:
        raise HTTPException(status_code=500, detail="Console API not configured (AKASH_CONSOLE empty)")

    # Try EVERY account, not just the first. The Console API scopes deployments
    # per account, so a deployment created under AKASH_CONSOLE_2 returns
    # "Deployment not found" when queried with AKASH_CONSOLE. Taking keys[0]
    # was safe only while a single account existed; with failover across
    # accounts it would report a live deployment as missing.
    # Sweep every account, then sweep again: Console's 404 is TRANSIENT.
    #
    # MEASURED 2026-08-10. dseq 1786369637481 answered 200 from account 2 on six
    # consecutive probes across three minutes, then 404 from ALL THREE accounts ~9
    # minutes later — with the lease still ACTIVE on-chain the whole time. The comment
    # further down this file already recorded the same phenomenon at day granularity
    # ("the same dseqs returned 200 from the same keys a day later"); this narrows it
    # to minutes.
    #
    # One sweep is therefore a coin flip, and losing it is not cheap: the caller falls
    # through to `lease-status --from=default`, which for a Console-owned deployment
    # can NEVER authenticate, so the 500 that reaches the E2E blames the wrong
    # subsystem entirely. A few seconds of retry costs nothing next to that.
    resp, last_err = None, None
    for attempt in range(_CONSOLE_STATUS_SWEEPS):
        if attempt:
            await asyncio.sleep(_CONSOLE_STATUS_RETRY_SEC)
        for key in keys:
            try:
                resp = await ConsoleApiBackend(api_key=key).get_deployment(deployment_id)
                break
            except Exception as e:
                last_err = e
                logger.debug("Console status miss for dseq=%s on one account: %s", deployment_id, e)
        if resp is not None:
            if attempt:
                logger.info(
                    "Console status for dseq=%s recovered on sweep %d/%d — transient upstream 404",
                    deployment_id,
                    attempt + 1,
                    _CONSOLE_STATUS_SWEEPS,
                )
            break
    if resp is None:
        # Console's index is blind to this deployment. Ask the PROVIDER, which knows its
        # own leases — MEASURED 2026-08-10: dseq 1786323569666 was ACTIVE on-chain and
        # owned by the querying account, Console said 404 on all three accounts, and the
        # provider returned the real per-service tally. Without this the caller falls
        # through to `lease-status --from=default`, which for a Console-owned deployment
        # can never authenticate, and /pods 500s for a workload that is running fine.
        pods = await _lease_status_pods_from_provider(deployment_id, data, keys)
        if pods is not None:
            return pods
        logger.warning(
            "Console API status query failed for dseq=%s across all %d account(s): %s",
            deployment_id,
            len(keys),
            last_err,
        )

        # THREE sources now agree this lease is gone: Console missed on every account across
        # all sweeps, the provider — which knows its own leases — also missed, and the
        # deployment's own record says closed. Stop here instead of running
        # `lease-status --from=default`, which cannot succeed and only obscures the answer.
        #
        # MEASURED 2026-08-12 (BLAZING-BACKEND-MH, 348 events/24h bursting ~2/min). Firestore
        # akash_deployments/{1786548976581,1786551257701,1786551256268} all read
        # status="closed" with wallet_key_name ABSENT, across THREE different providers.
        # 1786551257701 lived 16:14:40 -> 16:21:35, then was polled indefinitely. Each poll
        # ran the CLI cascade below: 3 attempts at 2s/4s backoff, ~10s wasted, then a 500
        # whose text blamed `--from=default`. That blame is ACCURATE — wallet_key_name really
        # is absent — but it is not the cause, which is why this was twice misdiagnosed as a
        # wallet-identity bug. Fixing the defaulting changes the message, not the burn.
        #
        # The corroboration is deliberately three-way. An earlier version of this guard keyed
        # on the Firestore status ALONE, before the Console read — and that is unsafe: several
        # writers stamp "closed" without ever confirming an on-chain close (see
        # _recorded_closed), and the wallet_key_name-absent shape they produce is exactly this
        # population. Reading the record first would have returned [] for a live,
        # escrow-burning lease, and the sweepers and reconciler both skip CLOSED, so nothing
        # downstream would have noticed. Asking the live sources FIRST keeps their answer
        # authoritative: a mislabelled document is harmless because Console or the provider
        # simply returns the running pods, exactly as today.
        #
        # 410, not 200-with-[] and not 500. It is an ERROR on purpose: e2e/lib/workloads_api.py
        # resets its consecutive-error counter on every SUCCESSFUL response, so returning an
        # empty list would disarm the only fail-fast that surfaces this and convert a ~50s loud
        # failure into a 900-1800s silent timeout. 410 GONE states the fact precisely — the
        # workload existed and no longer does — where 404 would conflate it with "never
        # existed" and 500 claims a server fault for a normal lifecycle event.
        if _recorded_closed(data):
            logger.info(
                "dseq=%s: Console and provider both report it gone and the record says closed "
                "— returning 410 without the lease-status cascade",
                deployment_id,
            )
            raise HTTPException(
                status_code=410,
                detail=(
                    f"Deployment {deployment_id} is closed: its lease no longer exists on "
                    f"Console or the provider, and its record is marked closed. No pods."
                ),
            )
        raise HTTPException(status_code=502, detail=f"Console API status query failed: {last_err}")

    if resp is None:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    status = str(getattr(resp.status, "value", resp.status)).lower()
    if status == "closed":
        return []

    ready = status in _AKASH_CONSOLE_RUNNING_STATUSES
    if status in _AKASH_CONSOLE_FAILED_STATUSES:
        phase = "Failed"
    elif ready:
        phase = "Running"
    else:
        phase = "Pending"

    # waiting_reason: surface the Console status verbatim so E2E logs show
    # whether the deployment is stuck bidding, leased-but-no-pods, etc.
    waiting_reason = None if ready or phase == "Failed" else f"console_status={status}"

    # pods_ready: first-time write-back when the Console reports the
    # deployment as actually serving traffic. B1b smoke and any caller that
    # treats "lease created" as "pods serving" can switch to this signal to
    # catch provider-delivery failures the akash_deployments.status field
    # misses (status="active" is set on lease creation, not on readiness).
    if ready and not data.get("pods_ready"):
        try:
            # The client must be awaited BEFORE chaining: `await x.collection()...`
            # binds the await to the outermost call, so .collection() would run on a
            # coroutine, raise AttributeError, and be swallowed by the except below —
            # silently never writing pods_ready back. (CodeRabbit #628)
            _db = await _get_firestore_client(firestore)
            await asyncio.to_thread(
                _db.collection("akash_deployments").document(deployment_id).update,
                {"pods_ready": True, "pods_ready_at": datetime.utcnow().isoformat()},
            )
        except Exception as exc:
            logger.warning(
                "Failed pods_ready write-back for console dseq=%s: %s",
                deployment_id,
                exc,
            )

    # One PodStatus PER REPLICA. The Console API reports deployment-level status with no
    # per-replica breakdown, so every entry carries the same synthesised status — but the
    # COUNT must match what the caller deployed, because callers poll on it.
    #
    # Returning a single entry unconditionally made every multi-replica Console workload
    # look permanently half-deployed. MEASURED 2026-08-01 (run 30705619597, D1-dfc):
    #
    #   poll_until(wait_pods_ready(akash-1785598935992, expected=2)): timed out after 900s
    #   Phase 3/6: Wait for Pods Ready — pods=[web: phase='Running' ready=True]
    #
    # The deployment was healthy and the one reported pod was Running AND ready; the test
    # simply never saw a second entry, burned the full 900s budget and failed. This only
    # became visible once #813 routed Console deployments here instead of 500-ing on
    # lease-status — that fix exposed this layer rather than causing it.
    #
    # `replicas` is already persisted on the deployment doc (deployment_router writes it;
    # the GKE sites in this file read it). Default 1, never 0 — a 0 would report "no pods"
    # for a live deployment, the falsy-default trap this repo keeps hitting.
    try:
        replica_count = int(data.get("replicas") or 1)
    except (TypeError, ValueError, OverflowError):
        # OverflowError too: int(float("inf")) raises it, so a non-finite replicas value
        # would have 500'd this endpoint instead of taking the documented fallback of 1.
        logger.warning("dseq=%s has non-numeric replicas=%r — reporting 1", deployment_id, data.get("replicas"))
        replica_count = 1
    replica_count = max(1, replica_count)

    base_name = data.get("worker_id") or f"akash-{deployment_id}"
    return [
        PodStatus(
            # Suffix only when there is more than one, so single-replica names stay
            # byte-identical for every existing caller and log line.
            name=base_name if replica_count == 1 else f"{base_name}-{i}",
            phase=phase,
            ready=ready,
            restart_count=0,
            started_at=None,
            waiting_reason=waiting_reason,
        )
        for i in range(replica_count)
    ]


async def _list_akash_pods(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
) -> List[PodStatus]:
    """List pods for an Akash/DFC deployment via lease-status."""
    db = await _get_firestore_client(firestore)

    # Look up deployment in Firestore
    doc = db.collection("akash_deployments").document(deployment_id).get()
    if not doc.exists:
        logger.warning(f"_list_akash_pods 404: document akash_deployments/{deployment_id} does not exist")
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    data = doc.to_dict()

    # Verify ownership
    if data.get("organization_id") != organization_id:
        logger.warning(
            f"_list_akash_pods 404: org mismatch for DSEQ {deployment_id}: "
            f"stored={data.get('organization_id')!r}, requested={organization_id!r}"
        )
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")
    if data.get("cluster_id") != cluster_id:
        logger.warning(
            f"_list_akash_pods 404: cluster mismatch for DSEQ {deployment_id}: "
            f"stored={data.get('cluster_id')!r}, requested={cluster_id!r}"
        )
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    # Console-API deployments have no local wallet — lease-status cannot query
    # them. AKASH_DEPLOYMENT_PRIMARY defaults to "console", so this is the
    # common path for DFC deployments. Query the Console API instead.
    #
    # DO NOT gate this on `wallet_backend == "console_api"`. That field is not a
    # trustworthy provenance signal: `deployment_router.py` persists
    # `response.wallet_backend or "self_managed"`, and the Console response often
    # carries no wallet_backend at all — so a Console-owned deployment is written to
    # Firestore labelled "self_managed". Reading it back then routed this function to
    # `provider-services lease-status`, which has no local keyring identity for a
    # Console-owned lease and fails with "remote server returned 404" on every
    # attempt — surfacing as `WorkloadsAPI Error 500` on
    # /workloads/akash-{dseq}/pods.
    #
    # MEASURED 2026-08-01 (run 30698461383, canary-pr-806): C2 Phase 6 and D1-dfc both
    # died on that 500 while running a canary that already carried the
    # AkashDeploymentResponse model fix (#806) — proving the pydantic mismatch was a
    # DIFFERENT defect, not this one.
    #
    # `handlers.akash.should_use_console_endpoints` already reached this conclusion for
    # the mesh-endpoint path (see its comment, MEASURED 2026-07-30 on canary-pr-785,
    # same "remote server returned 404" symptom). This is the sibling call site that
    # was never migrated. The reliable condition is "can we ask Console at all":
    # asking is cheap and side-effect-free, and for a genuinely wallet-owned
    # deployment Console reports not-found, which falls through to lease-status below.
    # Set before the Console attempt so the lease-status failure path can always read
    # it, whether or not Console was reached.
    console_error: Optional[str] = None

    _console_failure = ""
    from handlers.akash import should_use_console_endpoints  # noqa: PLC0415
    from services.console_keys import console_api_keys  # noqa: PLC0415

    if should_use_console_endpoints(wallet_backend=data.get("wallet_backend"), console_keys=console_api_keys()):
        try:
            return await _list_akash_pods_via_console(deployment_id, data)
        except HTTPException as e:
            # 404/502 = Console cannot see this deployment (wallet-owned, or not
            # visible on any configured account). Fall through to lease-status, which
            # is the correct path for those. Anything else is a real error: re-raise.
            if e.status_code not in (404, 502):
                raise
            # KEEP the Console error. Falling through on 502 is correct — a genuinely
            # wallet-owned deployment also surfaces as 502, since
            # `_list_akash_pods_via_console` raises 502 once every account has failed and
            # cannot distinguish "Console does not have it" from "Console is broken".
            # But DISCARDING the reason was wrong: when lease-status then fails (as it
            # always does for a Console-owned deployment) the caller saw only
            #   "Failed to query lease status after 3 attempts: remote server returned 404"
            # which names the wrong subsystem entirely. MEASURED 2026-08-01 (D1-dfc,
            # canary-pr-820): that message sent the investigation at lease-status while
            # the real failure was the Console query whose error had been logged at INFO
            # and thrown away. A fallback that swallows the diagnosis is the same defect
            # this handler was fixed for in #813 — reintroduced by #813 itself.
            console_error = e.detail
            logger.warning(
                "Console API has no view of dseq=%s (%s: %s) — falling back to lease-status",
                deployment_id,
                e.status_code,
                e.detail,
            )

    provider = data.get("provider_address")
    if not provider:
        raise HTTPException(status_code=500, detail="Deployment has no provider address")

    # Use the wallet key that created the deployment (pool wallets differ from "default").
    # `or` handles docs where the field exists but is None — `.get(..., "default")` only
    # defaults when the key is absent.
    #
    # `wallet_key_name_defaulted` records that we did NOT know who owns this deployment
    # and queried as `default` anyway. That is a guess about IDENTITY, and when it is
    # wrong the provider answers "remote server returned 404" — indistinguishable from
    # "the lease does not exist". Both readings appear in the error today and they point
    # at opposite investigations, so the guess has to be stated in the failure (#848).
    wallet_key_name = data.get("wallet_key_name") or "default"
    wallet_key_name_defaulted = not data.get("wallet_key_name")
    if wallet_key_name != "default" and wallet_key_name.startswith("wallet-"):
        # Pool wallet — import key into local keyring if not already present
        from handlers.logs import _ensure_pool_wallet_in_keyring

        imported = await _ensure_pool_wallet_in_keyring(wallet_key_name)
        if not imported:
            logger.warning(f"Could not import pool wallet {wallet_key_name} for lease-status on DSEQ {deployment_id}")

    keyring_backend = os.environ.get("AKASH_KEYRING_BACKEND", "test")
    rpc_node = os.environ.get("AKASH_RPC_NODE") or os.environ.get("AKASH_NODE", "https://rpc.akashnet.net:443")

    cmd = [
        "provider-services",
        "lease-status",
        f"--dseq={deployment_id}",
        f"--provider={provider}",
        "--from",
        wallet_key_name,
        f"--keyring-backend={keyring_backend}",
        f"--node={rpc_node}",
    ]

    max_retries = 3
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Deployment status check timed out")

        if result.returncode == 0:
            break  # Success -- proceed to parse

        last_error = result.stderr
        if attempt < max_retries:
            delay = 2**attempt  # 2s, 4s
            logger.warning(
                "lease-status for dseq=%s failed (attempt %d/%d): rc=%d, stderr=%s. Retrying in %ds...",
                deployment_id,
                attempt,
                max_retries,
                result.returncode,
                result.stderr[:200],
                delay,
            )
            await asyncio.sleep(delay)
    else:
        # All retries exhausted. If the Console path was tried first and failed, its
        # error is the more informative one — report BOTH rather than blaming
        # lease-status for a Console-owned deployment it could never have queried.
        detail = f"Failed to query lease status after {max_retries} attempts: {last_error}"
        # Name the IDENTITY the query used. A provider 404 means "you are not the owner
        # of this lease" just as readily as "no such lease", and without this the two are
        # indistinguishable in the error. MEASURED 2026-08-03 (#848): all three dfc legs
        # failed with a bare double-404 while the lease was ACTIVE on-chain the entire
        # time, and the message named neither the principal nor the recorded provenance.
        #
        # The Console half turned out to be a TRANSIENT upstream 404 — the same dseqs
        # returned 200 from the same keys a day later. Because the error named no
        # identity, that read as an authorization or configuration fault and the
        # investigation spent a day chasing account ownership. Stating the principal is
        # what separates "upstream cannot see it right now" from "we asked as the wrong
        # principal", which need opposite fixes.
        detail += (
            f" | queried as --from={wallet_key_name!r}"
            f"{' (DEFAULTED — the deployment doc has no wallet_key_name, so this is a guess at the owner)' if wallet_key_name_defaulted else ''}"
            f"; recorded wallet_backend={data.get('wallet_backend')!r}, provider={provider}"
        )
        if console_error:
            detail += f" | Console API was tried first and failed: {console_error}"
        raise HTTPException(status_code=500, detail=detail)

    try:
        status_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid lease status response: {str(e)}",
        )

    pods = []
    # lease-status output has services at top level, not nested under "result"
    services = status_data.get("services") or status_data.get("result", {}).get("services", {})

    any_ready = False
    for service_name, service_info in services.items():
        available = service_info.get("available", 0)
        total = service_info.get("total", 1)

        phase = "Running" if available > 0 else "Pending"
        ready = available > 0
        if ready:
            any_ready = True

        # waiting_reason: when the provider has the lease but no pods are
        # serving traffic (available=0), surface what the provider DOES
        # report so E2E logs can distinguish "manifest not delivered" from
        # "scheduled but unhealthy". Parsed from lease-status JSON.
        waiting_reason = None
        if not ready:
            parts = [f"available={available}/{total}"]
            replicas = service_info.get("replicas")
            ready_replicas = service_info.get("ready_replicas")
            if replicas is not None:
                parts.append(f"replicas={ready_replicas if ready_replicas is not None else '?'}/{replicas}")
            gen = service_info.get("observed_generation")
            if gen is not None:
                parts.append(f"gen={gen}")
            updated_replicas = service_info.get("updated_replicas")
            if updated_replicas is not None and updated_replicas != replicas:
                parts.append(f"updated={updated_replicas}")
            waiting_reason = "; ".join(parts)

        # Create one pod per replica
        num_replicas = max(total, 1)
        for i in range(num_replicas):
            pod_name = f"{service_name}-{i}" if num_replicas > 1 else service_name
            pods.append(
                PodStatus(
                    name=pod_name,
                    phase=phase,
                    ready=ready,
                    restart_count=0,
                    started_at=None,
                    waiting_reason=waiting_reason,
                )
            )

    # pods_ready: first-time write-back when the provider has actually
    # delivered pods (lease-status shows services.available>0). The
    # akash_deployments.status field is set to "active" on lease creation,
    # so it doesn't catch "lease formed but provider never ran the pods" —
    # this field does. Smoke tests can opt in to checking pods_ready to
    # close that observability gap.
    if any_ready and not data.get("pods_ready"):
        try:
            db.collection("akash_deployments").document(deployment_id).update(
                {"pods_ready": True, "pods_ready_at": datetime.utcnow().isoformat()}
            )
        except Exception as exc:
            logger.warning(
                "Failed pods_ready write-back for self_managed dseq=%s: %s",
                deployment_id,
                exc,
            )

    return pods


# Latitude VM/server status enum: Scheduling, Scheduled, Starting,
# "Configuring network", Running, Destroying. "Destroying" is the only
# terminal-failure state observable while waiting for a boot.
_LAT_RUNNING_STATUSES = {"running", "on"}
_LAT_FAILED_STATUSES = {"destroying", "failed"}


async def _list_lat_pods(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
) -> List[PodStatus]:
    """List pods for a LAT (Latitude.sh) deployment.

    LAT is the renamed DFN provider — Latitude.sh-based VMs (default) or
    bare-metal servers (opt-in). Unlike Akash/GKE, LAT has no
    Kubernetes/pod abstraction — each VM/server is one "pod" from the
    workloads-API perspective. Status is queried live via the Latitude
    SDK (no Firestore cache for VM state).

    resource_id is the Latitude vm_id (default, opaque token) or the
    bare-metal server_id (legacy/opt-in). The cluster metadata tells us
    which kind to look up.
    """
    from services.entity_store_factory import get_entity_store

    registry = get_entity_store()
    cluster_data = registry.get_cluster(organization_id, project_id, cluster_id)
    if cluster_data is None:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

    metadata = cluster_data.get("metadata") or {}
    if metadata.get("provider_kind") != "latitude":
        raise HTTPException(
            status_code=404,
            detail=f"Cluster {cluster_id} is not a Latitude cluster (provider_kind={metadata.get('provider_kind')!r})",
        )

    # Verify the resource_id matches what cluster metadata recorded — guards
    # against a stale workload_id being plumbed to a re-provisioned VM.
    expected_vm = str(metadata.get("latitude_vm_id") or "").strip()
    expected_server = str(metadata.get("latitude_server_id") or "").strip()
    is_vm = bool(expected_vm) and expected_vm == resource_id
    is_server = bool(expected_server) and expected_server == resource_id
    if not is_vm and not is_server:
        raise HTTPException(
            status_code=404,
            detail=f"Resource {resource_id} not registered on cluster {cluster_id}",
        )

    try:
        from latitude_client import LatitudeClient

        client = LatitudeClient()
        if is_vm:
            vm = client.get_vm_status(resource_id)
            raw_status = (vm.status or "unknown").lower()
            name = vm.name or resource_id
        else:
            server = client.get_server_status(resource_id)
            raw_status = (server.status or "unknown").lower()
            name = getattr(server, "name", None) or resource_id
    except HTTPException:
        raise
    except Exception as exc:
        # During a native reboot (the LAT "kill" — see _kill_lat_workload) the
        # host passes through a transitional state the SDK can't always parse
        # (live-probed: ResponseValidationError ~20s into a reboot). Surfacing a
        # hard 502 here would break the recovery test's /pods poll mid-cycle, so
        # treat a transient query error as Pending — the controller (test) keeps
        # polling until the host returns to running or the phase budget expires.
        logger.warning(
            "Latitude status query failed for resource=%s (treating as Pending): %s",
            resource_id,
            exc,
        )
        return [
            PodStatus(
                name=resource_id,
                phase="Pending",
                ready=False,
                restart_count=0,
                started_at=None,
                waiting_reason="lat_status_transitioning",
            )
        ]

    if raw_status in _LAT_FAILED_STATUSES:
        phase = "Failed"
        ready = False
    elif raw_status in _LAT_RUNNING_STATUSES:
        phase = "Running"
        ready = True
    else:
        phase = "Pending"
        ready = False

    waiting_reason = None if ready or phase == "Failed" else f"lat_status={raw_status}"

    # VM power state alone is NOT readiness: a running VM whose workload
    # container has crashed / not yet started (cloud-init still installing, or
    # mid-restart after the reboot "kill") would otherwise report ready=True
    # (masked a no-container condition for 15 min, 2026-06-12). When the VM is
    # up, probe the container over SSH (bounded pool, so it can't starve the
    # loop) and surface a waiting_reason that distinguishes the workload layer
    # from the network/infra layer:
    #   no_container → "lat_container_not_running" (real workload-down)
    #   unreachable  → "lat_vm_unreachable"        (infra/IP flake, mid-reboot)
    #   unknown      → keep VM-power readiness (no key → graceful degrade)
    if ready:
        vm_ip = str(metadata.get("latitude_vm_ip") or "").strip()
        if vm_ip:
            cstatus = await _run_in_lat_ssh_pool(_lat_container_status_sync, vm_ip)
            if cstatus == LAT_CONTAINER_NONE:
                phase = "Pending"
                ready = False
                waiting_reason = "lat_container_not_running"
            elif cstatus == LAT_VM_UNREACHABLE:
                phase = "Pending"
                ready = False
                waiting_reason = "lat_vm_unreachable"
            # LAT_CONTAINER_RUNNING → ready stays True
            # LAT_CONTAINER_UNKNOWN → no key to check → keep VM-power readiness

    return [
        PodStatus(
            name=name,
            phase=phase,
            ready=ready,
            restart_count=0,
            started_at=None,
            waiting_reason=waiting_reason,
        )
    ]


# =============================================================================
# Kill Workload (Unified)
# =============================================================================


class KillWorkloadRequest(BaseModel):
    pod_name: Optional[str] = Field(None, description="Specific pod to kill (GKE only)")
    grace_period: int = Field(0, ge=0, le=300, description="Grace period in seconds")


@workloads_router.post(
    "/{workload_id}/kill",
    summary="Kill a workload pod or container",
    description="""
Kill a pod (GKE) or send kill signal to container (Akash/DFC).

**GKE:** Deletes the specified pod via K8s API. The StatefulSet/Deployment controller
will recreate it automatically.

**Akash/DFC:** Sends kill -9 1 inside the container via provider-services lease-shell.
The provider restarts the container automatically (soft kill).

**CronJob:** Returns 400 (not applicable).
""",
)
async def kill_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    request: KillWorkloadRequest,
    organization: Dict = Depends(get_current_organization),
):
    """Kill a workload pod or container."""
    logger.info(f"[{organization_id}] Kill workload: {workload_id}")

    workload_type, resource_id = _parse_workload_id(workload_id)

    if workload_type == "gke_worker":
        return await _kill_gke_worker(
            organization_id,
            cluster_id,
            resource_id,
            request.pod_name,
            request.grace_period,
        )
    elif workload_type == "akash_deployment":
        return await _kill_akash_deployment(organization_id, cluster_id, resource_id, request.grace_period)
    elif workload_type == "lat_deployment":
        return await _kill_lat_workload(organization_id, project_id, cluster_id, resource_id, request)
    elif workload_type == "cronjob":
        return _kill_cronjob()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")


async def _kill_gke_worker(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
    pod_name: Optional[str],
    grace_period: int,
) -> Dict[str, Any]:
    """Kill a GKE worker pod via K8s Python client."""
    db = await _get_firestore_client(firestore)

    # Look up worker in Firestore (gke_deployments first, workers legacy fallback)
    data = _resolve_gke_worker(db, organization_id, cluster_id, worker_id)
    namespace = data.get("namespace", f"c-{cluster_id}")

    # Find a running pod for this worker.
    # Deployments use random suffixes (worker-tetris-abc123),
    # StatefulSets use ordinal (worker-tetris-0).
    # Use label selector to find the actual pod name.
    if not pod_name:
        try:
            v1 = k8s_client.CoreV1Api()
            pods = v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"worker-id={worker_id}",
            )
            running_pods = [p for p in pods.items if p.status.phase == "Running"]
            if running_pods:
                pod_name = running_pods[0].metadata.name
            elif pods.items:
                pod_name = pods.items[0].metadata.name
            else:
                raise HTTPException(status_code=404, detail=f"No pods found for worker {worker_id}")
        except ApiException as e:
            raise HTTPException(status_code=e.status or 500, detail=f"K8s API error: {e.reason}")

    try:
        v1 = k8s_client.CoreV1Api()
        v1.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            grace_period_seconds=grace_period,
        )
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Pod {pod_name} not found")
        raise HTTPException(status_code=e.status or 500, detail=f"K8s API error: {e.reason}")

    logger.info(f"[{organization_id}] Killed GKE pod {pod_name} in {namespace}")
    return {
        "workload_id": f"worker-{worker_id}",
        "killed_pod": pod_name,
        "status": "killed",
    }


# Positive evidence that a lease-shell invocation never reached the container. Kept
# narrow ON PURPOSE: `kill -9 1` legitimately produces a non-zero exit (it tears down
# PID 1), so the discriminator must be the failure text, never the exit code alone.
# Every entry below was observed on this path:
#   "key not found" / "default.info"  - no local keyring identity (Console-owned)
#   "lease shell failed"              - provider refused the session outright
#   "remote server returned 404"      - wrong identity, or the lease is gone
#   "unauthorized" / "JWT is invalid" - the Console-JWT route was rejected
#   "[CONSOLE-SHELL] ... failed on"   - our own marker: every account exhausted
#   "circuit breaker"                 - fast-failed before any request left the process
# ★ THE EXEC LAYER'S INDETERMINATE SENTINEL — it means UNKNOWN, not "never ran".
#
# `-1` is not a process exit code: a real `kill -9 1` cannot produce it, so a `-1` always
# means the exec layer itself gave up rather than the command returning a status. But it does
# NOT say WHY. On `origin/main`, `_exec_akash_deployment`'s only literal `-1` is its
# `asyncio.TimeoutError` handler:
#
#     except asyncio.TimeoutError:
#         process.kill()
#         return {"exit_code": -1, "stderr": f"Command timed out after {timeout}s", ...}
#
# A timeout is NOT evidence the command failed to reach the container. It is evidence the
# client stopped waiting — and for THIS command that is ambiguous in the worst way, because
# `kill -9 1` tears down PID 1 and the shell session dies mid-command. A hung client is a
# plausible shape of the SUCCESS case, which is exactly why the guard below cannot assert
# non-delivery. Doing so would 502 on kills that worked.
#
# ⚠ WHAT IS NOT ESTABLISHED: that no other path can yield -1. The only claims verified are
# that `:3556` is the sole LITERAL -1 inside `_exec_akash_deployment`, and that `ExecResult`
# / `container_exec` — the workers-layer sentinel an earlier revision of this comment cited —
# is not referenced in this file at all. `_resp.exit_code` (the Console-shell path) is
# delegated and untraced; a -1 could originate there with different semantics. So the honest
# reading is narrow: `-1` is NOT exclusively a non-delivery marker, and at least one producer
# of it means timeout. That is enough to forbid "exit=-1 ⇒ never reached the container"; it
# is not a proof of the converse.
#
# MEASURED run 31514389709, C0: Pod Recovery (dfc):
#     17:21:57  Soft-killed Akash deployment 1786468883565 service=tetris exit=-1
# and the leg reported PASS, while its own `poll_until(pod leaves Running state)` FAILED —
# the pod never moved. The denylist below could not save it: a list of known failure phrases
# is incomplete by construction, and this stderr matched none of them.
#
# ★ SO THE ANSWER IS A THIRD STATE. The status quo was a hollow PASS; asserting non-delivery
# would be a confident FAIL that is sometimes wrong. An ambiguous status is resolved by saying
# UNKNOWN — not by picking whichever confident answer is convenient. A false FAIL beats a
# hollow PASS, and UNKNOWN is how to get that honesty without inventing a certainty we do not
# have. (Same shape as recording `p99_completed_s` while leaving `threshold_s: null` in
# e2e/measured-thresholds.json: the observation is real, it does not license the conclusion.)
_EXEC_INDETERMINATE_EXIT_CODE = -1

# The three outcomes a kill can have. Named, because a two-valued decision is what produced
# both the hollow PASS and the over-confident FAIL this replaces.
_KILL_DELIVERED = "delivered"
_KILL_NOT_REACHED = "not_reached"
_KILL_UNKNOWN = "unknown"


def _classify_kill_outcome(exit_code: Any, stderr_text: str) -> str:
    """Three-valued: delivered / not_reached / unknown. Never two.

    ORDER MATTERS. Positive stderr evidence of non-delivery is checked FIRST, so a -1 that
    also says "key not found" is reported as the non-delivery it is, rather than downgraded
    to UNKNOWN. Only a -1 with no such evidence is indeterminate.

    `exit_code == 0` and `None` are DELIVERED and must stay that way: `kill -9 1` tears down
    PID 1, so a non-zero exit — or the session dying — is the SUCCESS shape here. Asserting
    `exit_code == 0` would invert the bug.
    """
    if exit_code not in (0, None) and _kill_never_reached_container(stderr_text):
        return _KILL_NOT_REACHED
    if exit_code == _EXEC_INDETERMINATE_EXIT_CODE:
        return _KILL_UNKNOWN
    return _KILL_DELIVERED


_KILL_NOT_REACHED_MARKERS = (
    "key not found",
    "default.info",
    "lease shell failed",
    "remote server returned 404",
    "unauthorized",
    "jwt is invalid",
    "failed on all",
    "circuit breaker",
)


def _kill_never_reached_container(stderr_text: str) -> bool:
    """True only when stderr positively shows the command never ran in the container."""
    low = (stderr_text or "").lower()
    return any(m in low for m in _KILL_NOT_REACHED_MARKERS)


# ★ THE KILL MUST PROVE IT EXECUTED (#1177, #1175).
#
# MEASURED: `exit=0` and `exit=-1` are two faces of the SAME early return. On 26/26 dfc
# C0 greens the pod never left Running, and the API-side logs show the exec returning in
# 132-486ms against a just-akash baseline of p50 1840ms for a WORKING exec (#958). So a
# zero here never meant the command ran, and the old two-valued judgement reported it as
# `{"status": "killed"}`.
#
# ⚠ `interpret_success()` in akash_lease_core CANNOT be used for this command: its first
# rule is `exit_code != 0 -> False`, and `kill -9 1` tears down PID 1 so the session dies
# and a non-zero exit is the SUCCESS shape. That helper is correct for ordinary commands
# and pinned cross-repo; the judgement below is made here instead of changing it.
#
# The only signal that survives a command which destroys its own shell is a marker echoed
# BEFORE the kill. If it comes back, the command reached the container and began running.
#
# ⚠ THE ASYMMETRY MATTERS AND IS THE WHOLE REASON THIS FAILS CLOSED RATHER THAN ASSERTING.
# `akash_lease_core.interpret_success` calls marker-echo "the only signal that survives both
# failure modes A and B", and its `is_unverified_success` names mode A as a DROPPED-STDOUT
# RACE. ⇒ Marker PRESENCE is sound evidence the command ran. Marker ABSENCE is NOT evidence
# it did not — mode A is precisely "it printed and the stdout was lost".
#
# ⚠ PRACTICAL RISK, NOT A LOGICAL ONE: if that race is common on this path, the ack reads
# absent whether or not the kill works, and this leg becomes permanently UNDETERMINED. An
# instrument that always reads "undetermined" is as useless as one that always reads "pass";
# we would have traded a false green for a permanent red nobody can act on. The deciding
# number is the drop rate on this transport and it is NOT MEASURED. If the first runs show
# UNDETERMINED with no observed departures either, that is the number to get before
# concluding anything about the kill.
# ⛔ THE ACK IS NOT MADE REDUNDANT BY #1211. I claimed it would be; that was wrong, and
# DEV2 — who owns #1211 — retracted the same claim independently.
#
# #1211 gives each of exec_command's seven `-1` producers a distinct `reason`. That makes
# the producers DISTINGUISHABLE. It does not make the OUTCOME decidable, because producers
# 5 and 7 (ConnectionClosed / no RESULT frame) both mean "the session ended" — and for
# `kill -9 1` a session ending is BOTH the success shape (PID 1 died, taking the shell with
# it) and the failure shape (the socket died before delivery). The `reason` names which code
# path fired; the code path is IDENTICAL in both cases, because exec_command cannot see
# inside the container.
#
# ⇒ The ack is evidence from INSIDE the container, which is the only place the difference
# exists. It stays necessary after #1211 lands. Removing either one on the belief that the
# other covers it loses a distinction nothing else carries.
_KILL_ACK = "DF-KILL-ACK"
_KILL_TIMEOUT_SEC = 30

# Four outcomes. The two-valued version produced a hollow PASS; the three-valued one could
# not tell a transport that never came up from a client that stopped waiting.
_KILL_EXECUTED_OK = "executed_succeeded"
_KILL_EXECUTED_FAILED = "executed_failed"
_KILL_NEVER_EXECUTED = "never_executed"
_KILL_UNDETERMINED = "undetermined"

# stderr proving `kill` itself RAN and was refused — the container answered.
_KILL_RAN_AND_REFUSED = ("operation not permitted", "no such process", "permission denied")

# ⚠ ELAPSED TIME IS EVIDENCE, and the old handler discarded it. `exit=-1` after the full
# budget means "we stopped listening" — the command may well have run. `exit=-1` in a small
# fraction of the budget means the transport declined before the command could have run.
# MEASURED on run 32200432961: 0.78s against a 30s budget, narrated to the operator as
# "the command TIMED OUT". Same sentinel, opposite meaning.
_EARLY_RETURN_FRACTION = 0.5


def _classify_kill_outcome_v2(
    exit_code: Any,
    stdout_text: str,
    stderr_text: str,
    duration_ms: Any,
    timeout_sec: int = _KILL_TIMEOUT_SEC,
) -> tuple:
    """Four-valued: (outcome, reason). Never fewer.

    ORDER MATTERS.

    1. The ack proves the command reached the container. Judge success/failure on stderr.
    2. Positive stderr evidence of non-delivery, as before.
    3. The indeterminate sentinel, split by ELAPSED TIME — the discriminator the handler
       already held and threw away.
    4. ★ `exit_code in (0, None)` with NO ack is UNDETERMINED, not delivered. This is the
       fail-open being closed: it is exactly the reading that produced 26/26 hollow greens.
    """
    ack = _KILL_ACK in (stdout_text or "")
    low = (stderr_text or "").lower()

    if ack:
        if any(m in low for m in _KILL_RAN_AND_REFUSED):
            return _KILL_EXECUTED_FAILED, "the container ran `kill` and refused it"
        # ⚠ THE ACK PROVES THE SHELL RAN, NOT THAT PID 1 DIED. `echo` succeeding says the
        # container was reachable and executed the command line; it says nothing about
        # whether `kill -9 1` then took effect. Those come apart exactly when the
        # container is unhealthy — which is the case the leg exists to detect. Effect is
        # the LEG's to observe (the pod must leave Running); this handler reports
        # DELIVERY only, and must not be read as a recovery verdict.
        return (
            _KILL_EXECUTED_OK,
            "the container echoed the ack, so the command line RAN (effect on PID 1 not established here)",
        )

    if _kill_never_reached_container(stderr_text):
        return _KILL_NEVER_EXECUTED, "stderr positively reports the command never reached the container"

    if exit_code == _EXEC_INDETERMINATE_EXIT_CODE:
        try:
            elapsed = float(duration_ms)
        except (TypeError, ValueError):
            # ⚠ An unreadable duration must NOT buy the confident branch.
            return _KILL_UNDETERMINED, "indeterminate sentinel and the elapsed time was not reported"
        if elapsed < _EARLY_RETURN_FRACTION * timeout_sec * 1000:
            # ⛔ THIS WAS `NEVER_EXECUTED` AND THAT WAS INVERTED (caught by DEV2 on #1213).
            #
            # An EMPTY stderr does not merely fail to prove non-delivery — it positively
            # EXCLUDES a timeout, because both timeout routes in exec_command always write
            # "Timeout after <n>s". What remains is a session that ended before a result,
            # and for `kill -9 1` a session ending IS the success shape: the command tears
            # down PID 1, which is the process the shell is attached to.
            #
            # So this reading is consistent with a kill that WORKED and with a socket that
            # died before delivery, and nothing in the response separates them.
            # ⇒ UNDETERMINED, never non-delivery.
            return (
                _KILL_UNDETERMINED,
                "the exec layer returned its indeterminate sentinel after %.0fms of a %ds budget with "
                "an empty stderr. That EXCLUDES a timeout (both timeout paths write 'Timeout after Ns') "
                "and leaves A SESSION THAT ENDED BEFORE A RESULT — which has at least three causes this "
                "response cannot separate: (a) the kill WORKED and tore down PID 1, the process the "
                "shell was attached to; (b) the transport dropped before delivery; (c) something at the "
                "POD OR HOST layer terminated the container independently of this command. "
                "⚠ (c) is not hypothetical: on 2026-08-19T08:09:23Z six CI runners died at the pod/host "
                "layer on our own Sofia cluster while every lease stayed OPEN for a further 40-44min. "
                "A host killing the container is neither a timeout nor a transport drop, and nothing in "
                "an `exit=-1` distinguishes it. The outcome is genuinely undetermined" % (elapsed, timeout_sec),
            )
        return (
            _KILL_UNDETERMINED,
            "the exec layer gave up after %.0fms of a %ds budget; the command may have run" % (elapsed, timeout_sec),
        )

    return (
        _KILL_UNDETERMINED,
        "the exec returned exit=%r with no ack in stdout. ⚠ MARKER ABSENCE IS NOT EVIDENCE OF "
        "NON-EXECUTION: akash_lease_core names a DROPPED-STDOUT RACE (its failure mode A) in "
        "which the command runs, prints, and the stdout is lost in transport. So this is "
        "consistent with THREE things and separates none of them — the kill never started, the "
        "kill ran and its ack was dropped, or the kill ran and the ack was still in flight when "
        "`kill -9 1` tore down PID 1" % (exit_code,),
    )


async def _kill_akash_deployment(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
    grace_period: int,
) -> Dict[str, Any]:
    """Kill an Akash/DFC container via lease-shell kill -9 1 (soft kill)."""
    db = await _get_firestore_client(firestore)

    doc = db.collection("akash_deployments").document(deployment_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    data = doc.to_dict()

    # Verify ownership
    if data.get("organization_id") != organization_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")
    if data.get("cluster_id") != cluster_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    status = data.get("status")
    if status not in ("active", "leased"):
        raise HTTPException(status_code=400, detail="Deployment is not active")

    provider = data.get("provider_address")
    if not provider:
        raise HTTPException(status_code=500, detail="Deployment has no provider address")

    service_name = data.get("service_name") or data.get("worker_id")
    if not service_name:
        raise HTTPException(status_code=500, detail="Could not determine service name")

    # Route through the shared exec path rather than shelling out here.
    #
    # This function built its own `provider-services lease-shell` invocation, which
    # authenticates with a LOCAL keyring identity — something a Console-owned deployment
    # does not have, so for every DFC workload the kill could not succeed. Meanwhile
    # `_exec_akash_deployment` already tries the Console JWT shell first and falls back
    # to the CLI, and (as of the previous commit) resolves the provider host from the
    # chain so it survives Console's index going blind. Delegating gives the kill that
    # same reach instead of a second, weaker copy of the same call.
    #
    # The argv it builds is identical in shape — `… -- <service> kill -9 1` — except
    # `--from` carries the OWNING wallet rather than a hardcoded "default".
    _exec = await _exec_akash_deployment(
        organization_id=organization_id,
        cluster_id=cluster_id,
        deployment_id=deployment_id,
        # ⚠ The ack is echoed BEFORE the kill on purpose: `kill -9 1` destroys the shell
        # that would have printed anything afterwards, so a trailing marker can never
        # arrive. A leading one proves the container reached the command.
        # ⛔ DO NOT WRAP THIS IN `sh -c`. `build_direct_provider_ws_url` in akash_lease_core
        # ALREADY emits `cmd0=/bin/sh&cmd1=-c&cmd2=<joined argv>`, and it joins the list with
        # plain spaces — so `["sh","-c","echo X; kill -9 1"]` reaches the container as
        # `/bin/sh -c 'sh -c echo X; kill -9 1'`. The inner quoting is LOST, `sh -c echo`
        # runs with the marker consumed as $0, and the ack SILENTLY NEVER PRINTS.
        # MEASURED: `sh -c 'sh -c echo DF-KILL-ACK'` -> empty stdout.
        # This list joins to `echo DF-KILL-ACK; kill -9 1`, which the builder's own
        # `/bin/sh -c` then runs correctly.
        command=["echo", "%s;" % _KILL_ACK, "kill", "-9", "1"],
        timeout=_KILL_TIMEOUT_SEC,
    )
    stderr_text = str(_exec.get("stderr") or "")
    stdout_text = str(_exec.get("stdout") or "")
    exit_code = _exec.get("exit_code")
    duration_ms = _exec.get("duration_ms")

    # Judge whether the kill REACHED the container.
    #
    # This handler used to read neither the return code nor stderr: only a timeout could
    # produce a non-200, so `{"status": "killed"}` was returned even when the subprocess
    # had failed without touching the workload. For DFC that is not hypothetical — the
    # command authenticates with a LOCAL keyring identity, and a Console-owned deployment
    # has none, so it cannot succeed. MEASURED run 31388705036: C0(dfc) reported
    # "Phase 4: Kill Pod PASS (3.61s)" and then spent 900s waiting for a recreation that
    # could not happen. `tests/test_exec_uses_the_owning_wallet.py` recorded this tension
    # as unresolved (#931); this resolves it — Phase 4 proved less than it appeared to.
    #
    # ⚠ A non-zero exit is NOT evidence of failure here. `kill -9 1` tears down PID 1, so
    # the shell session dying mid-command is the SUCCESS case; asserting exit_code == 0
    # would invert the bug and start failing on kills that worked. So judge on positive
    # evidence of NOT reaching the container instead — the identity/transport failures
    # measured on this path — and stay silent otherwise.
    _outcome, _reason = _classify_kill_outcome_v2(exit_code, stdout_text, stderr_text, duration_ms, _KILL_TIMEOUT_SEC)

    # ⚠ THE FOUR OUTCOMES MUST STAY FOUR ON THE WAY OUT (#1165's outbound half). Three of
    # them are non-200, and it would be easy to let them share one 502 body — which would
    # rebuild, inside this fix, exactly the collapse the fix exists to remove. Each carries
    # a distinct `outcome` field and a distinct sentence.
    _evidence = {
        "outcome": _outcome,
        "reason": _reason,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "ack_observed": _KILL_ACK in stdout_text,
        "stdout": stdout_text.strip()[:400],
        "stderr": stderr_text.strip()[:400],
    }

    if _outcome == _KILL_EXECUTED_FAILED:
        raise HTTPException(
            status_code=502,
            detail=(
                f"kill EXECUTED and FAILED for dseq={deployment_id}: the container ran the command "
                f"and refused it. This is not a delivery problem — the workload is reachable and "
                f"declined to die. {_reason}. evidence={_evidence}"
            ),
        )

    if _outcome == _KILL_NEVER_EXECUTED:
        raise HTTPException(
            status_code=502,
            detail=(
                f"kill NEVER EXECUTED for dseq={deployment_id}: {_reason}. "
                f"⚠ Do not read this as a timeout and do not retry expecting a different transport. "
                f"evidence={_evidence}"
            ),
        )

    if _outcome == _KILL_UNDETERMINED:
        raise HTTPException(
            status_code=502,
            detail=(
                f"kill outcome UNDETERMINED for dseq={deployment_id}: {_reason}. "
                f"⚠ This 502 FAILS CLOSED ON PURPOSE and will red a leg whose kill may have "
                f"succeeded. That is deliberate — a false red is recoverable, the false GREEN it "
                f"replaces was not (26/26 C0(dfc) greens never killed the pod). "
                f"⛔ ONLY A LIVE OBSERVATION CAN SETTLE THIS, AND ONLY DURING THE RUN. CI cleanup "
                f"tears the cluster down within minutes; a later query returns 'Cluster not found', "
                f"so every occurrence destroys its own evidence and the outcome becomes permanently "
                f"unknowable (measured on 9 of 9 instances). Do not plan to investigate one "
                f"afterwards — there is nothing left to read. The leg's pod observation, taken "
                f"while the run is live, is the only thing that can decide it; this handler cannot. "
                f"The pod may or may not have been killed — this is not a report that it was not, "
                f"and it is not a report that the command never ran. Both would be a guess. "
                f"evidence={_evidence}"
            ),
        )

    logger.info(
        f"[{organization_id}] Killed Akash deployment {deployment_id} service={service_name} "
        f"exit={exit_code} duration_ms={duration_ms} ack=yes"
    )
    return {
        "workload_id": f"akash-{deployment_id}",
        "killed_pod": service_name,
        "status": "killed",
        "mode": "soft",
        # Report the evidence rather than only the conclusion, so a caller can tell a
        # torn-down PID 1 from a command that quietly did nothing.
        **_evidence,
    }


def _kill_cronjob() -> None:
    """CronJob kill is not applicable."""
    raise HTTPException(status_code=400, detail="Kill operation is not applicable to CronJob workloads")


async def _kill_lat_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
    request: "KillWorkloadRequest",
) -> Dict[str, Any]:
    """Kill a LAT (Latitude) workload by rebooting its VM (or bare-metal server).

    LAT recovery is **VM-level** (design decision 2026-05-31, supersedes the
    container-level sketch in issue #270): Latitude is pure IaaS with no
    container runtime of its own, so "kill" uses Latitude's native power
    action to **reboot** the VM/server. Recovery is the host returning to
    ``running`` — observed by ``_list_lat_pods`` (the VM-as-pod status from
    PR #302) as the ``Running → starting → Running`` cycle. This is the
    idiomatic IaaS analogue of GCP's pod-delete and DFC's in-container
    ``kill -9 1``: each uses the platform's native control plane.

    No SSH / Docker / credentials — the previous SSH+``docker kill`` path
    (and its ``LAT_SSH_PRIVATE_KEY`` 501 guard) was removed in favour of the
    provider API. Probed live 2026-05-31: the reboot cycle completes in ~37s.
    """
    from services.entity_store_factory import get_entity_store

    registry = get_entity_store()
    cluster_data = registry.get_cluster(organization_id, project_id, cluster_id)
    if cluster_data is None:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
    metadata = cluster_data.get("metadata") or {}
    if metadata.get("provider_kind") != "latitude":
        raise HTTPException(
            status_code=404,
            detail=f"Cluster {cluster_id} is not a Latitude cluster",
        )

    # Route VM vs bare-metal by what the cluster metadata recorded at provision
    # time (mirrors _list_lat_pods). Guards against a stale workload_id pointing
    # at a re-provisioned host.
    expected_vm = str(metadata.get("latitude_vm_id") or "").strip()
    expected_server = str(metadata.get("latitude_server_id") or "").strip()
    is_vm = bool(expected_vm) and expected_vm == resource_id
    is_server = bool(expected_server) and expected_server == resource_id
    if not is_vm and not is_server:
        raise HTTPException(
            status_code=404,
            detail=f"Resource {resource_id} not registered on cluster {cluster_id}",
        )

    try:
        from latitude_client import LatitudeClient

        client = LatitudeClient()
        if is_vm:
            client.reboot_vm(resource_id)
        else:
            client.reboot_server(resource_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("LAT reboot failed for resource=%s: %s", resource_id, exc)
        raise HTTPException(status_code=502, detail=f"Latitude reboot failed: {exc}")

    logger.info("[%s] LAT reboot kill: rebooted %s", organization_id, resource_id)
    return {
        "workload_id": f"lat-{resource_id}",
        "killed_pod": resource_id,
        "status": "killed",
        "mode": "reboot",  # native Latitude power action
    }


# =============================================================================
# Exec Workload (Unified REST - Non-Interactive)
# =============================================================================


class ExecWorkloadRequest(BaseModel):
    command: List[str] = Field(..., description="Command to execute")
    pod_name: Optional[str] = Field(None, description="Specific pod (GKE only)")
    container: Optional[str] = Field(
        None, description="Container name (GKE and LAT; for LAT it is the docker --name, i.e. the service name)"
    )
    timeout: int = Field(30, ge=1, le=300, description="Timeout in seconds")


@workloads_router.post(
    "/{workload_id}/exec",
    summary="Execute a command in a workload container",
    description="""
Non-interactive command execution in a workload container. Returns stdout, stderr, and exit code.

**GKE:** Uses kubectl exec subprocess.
**Akash/DFC:** Uses provider-services lease-shell subprocess.
**CronJob:** Returns 400 (not applicable).

For interactive shell sessions, use the WebSocket exec endpoint instead.
""",
)
async def exec_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    request: ExecWorkloadRequest,
    organization: Dict = Depends(get_current_organization),
):
    """Execute a command in a workload container (non-interactive REST)."""
    logger.info(f"[{organization_id}] Exec workload: {workload_id}")

    workload_type, resource_id = _parse_workload_id(workload_id)

    if workload_type == "gke_worker":
        return await _exec_gke_worker(
            organization_id,
            cluster_id,
            resource_id,
            request.command,
            request.pod_name,
            request.container,
            request.timeout,
        )
    elif workload_type == "akash_deployment":
        return await _exec_akash_deployment(
            organization_id,
            cluster_id,
            resource_id,
            request.command,
            request.timeout,
        )
    elif workload_type == "cronjob":
        raise HTTPException(status_code=400, detail="Exec is not applicable to CronJob workloads")
    elif workload_type == "lat_deployment":
        return await _exec_lat_deployment(
            organization_id,
            project_id,
            cluster_id,
            resource_id,
            request.command,
            request.timeout,
            request.container,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")


async def _exec_gke_worker(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
    command: List[str],
    pod_name: Optional[str],
    container: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    """Execute a command in a GKE worker pod via kubectl subprocess."""
    db = await _get_firestore_client(firestore)

    # Look up worker in Firestore (gke_deployments first, workers legacy fallback)
    data = _resolve_gke_worker(db, organization_id, cluster_id, worker_id)
    namespace = data.get("namespace", f"c-{cluster_id}")

    # Derive pod name if not provided (StatefulSet convention)
    if not pod_name:
        pod_name = f"worker-{worker_id}-0"

    # Build kubectl exec command
    cmd = ["kubectl", "exec", pod_name, "-n", namespace]
    if container:
        cmd.extend(["-c", container])
    cmd.append("--")
    cmd.extend(command)

    start = time.monotonic()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "duration_ms": duration_ms,
        }

    duration_ms = int((time.monotonic() - start) * 1000)
    return {
        "exit_code": process.returncode or 0,
        "stdout": stdout_bytes.decode("utf-8", errors="replace"),
        "stderr": stderr_bytes.decode("utf-8", errors="replace"),
        "duration_ms": duration_ms,
    }


async def _exec_akash_deployment(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
    command: List[str],
    timeout: int,
) -> Dict[str, Any]:
    """Execute a command in an Akash/DFC container via lease-shell subprocess."""
    db = await _get_firestore_client(firestore)

    doc = db.collection("akash_deployments").document(deployment_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    data = doc.to_dict()

    # Verify ownership
    if data.get("organization_id") != organization_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")
    if data.get("cluster_id") != cluster_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    status = data.get("status")
    if status not in ("active", "leased"):
        raise HTTPException(status_code=400, detail="Deployment is not active")

    provider = data.get("provider_address")
    if not provider:
        raise HTTPException(status_code=500, detail="Deployment has no provider address")

    service_name = data.get("service_name") or data.get("worker_id")
    if not service_name:
        raise HTTPException(status_code=500, detail="Could not determine service name")

    # Resolve the wallet that actually owns this deployment, and make sure its key is
    # in the local keyring, BEFORE shelling out.
    #
    # This path used to hardcode `--from default`. There is no key named `default` when
    # the wallet pool is off or the deployment is Console-owned, so every exec died with
    #
    #     Error: lease shell failed: the provider encountered an unknown error
    #
    # MEASURED 2026-08-08: that broke C1 (dfc) Phase 6 on every run — `pg_isready` is
    # probed INSIDE the container through this call, so a dead exec channel made the
    # recovery assertion unprovable. The leg could then only report `skip`, and
    # `ci_merge_gate_c_tier.py` blocks on skip ("the leg never ran"), which deadlocked
    # every PR behind it. The 300s in those logs was never a slow Postgres; it was this
    # poll exhausting while every probe failed on identity.
    #
    # Same defect as the E1 mesh fix earlier today (`provider-services … --from default`),
    # surviving in a second call site. The correct pattern already lived ~700 lines up in
    # the lease-status path; this mirrors it.
    # No local wallet identity -> use the Console-authenticated shell instead.
    #
    # MEASURED on run 31312782613 via the invocation diagnostic below:
    #
    #     [LEASE-SHELL INVOCATION] dseq=1786279996707 provider=akash1z9nr23…
    #                              --from=default (defaulted=True)
    #
    # `defaulted=True` means the deployment record carries no wallet_key_name. Both write
    # sites DO persist it (`akash_client.py:2602/:5274`), so its absence is not a bug —
    # DFC deploys through the Console API as primary, which signs with a Console account
    # and never mints a local keyring wallet. There is nothing to record.
    #
    # `provider-services lease-shell` can only authenticate with a local key, so for these
    # deployments it fails on EVERY call with the provider's opaque
    # "the provider encountered an unknown error". That is what makes C1 (dfc) Phase 6
    # unprovable: it probes pg_isready through this function, the leg can only report
    # `skip`, and `ci_merge_gate_c_tier.py` blocks on skip (#930/#931).
    #
    # `ConsoleApiBackend.exec_shell` already solves exactly this — it chains
    # create_shell_token -> ProviderShellClient.with_jwt -> exec_command, "bypassing the
    # provider-services CLI entirely". It existed and this path never used it.
    #
    # Scoped deliberately: this branch is taken ONLY when there is no wallet_key_name,
    # i.e. only where the CLI path is guaranteed to fail today. Deployments that DO carry
    # a wallet keep the existing behaviour untouched, so this cannot regress them.
    from handlers.akash import should_use_console_endpoints  # noqa: PLC0415
    from services.console_keys import console_api_keys  # noqa: PLC0415

    _console_keys = console_api_keys()
    if should_use_console_endpoints(wallet_backend=data.get("wallet_backend"), console_keys=_console_keys):
        # Try EVERY account, not just the first. The Console API scopes deployments per
        # account, so one created under AKASH_CONSOLE_2 returns "not found" when queried
        # with AKASH_CONSOLE — the same reason the lease-status path above iterates.
        #
        # Gated on keys being configured: without one there is nothing to authenticate
        # WITH, and attempting the call would put a network round-trip into unit tests
        # that mock `create_subprocess_exec`, slowing or hanging them for no benefit.
        _shell_errors = []
        for _key in _console_keys:
            try:
                from services.console_api_backend import ConsoleApiBackend

                _shell_start = time.monotonic()
                _resp = await ConsoleApiBackend(api_key=_key).exec_shell(
                    dseq=str(deployment_id),
                    command=" ".join(shlex.quote(c) for c in command),
                    service_name=service_name,
                    timeout=int(timeout),
                    # Hand over the provider we already recorded. With it, exec_shell
                    # resolves the host from the chain and never touches Console's
                    # index — which 404'd mid-leg in run 31400468684 and failed the
                    # exec on all three accounts.
                    provider_address=data.get("provider_address"),
                )
                logger.info(
                    f"[CONSOLE-SHELL] dseq={deployment_id} service={service_name} "
                    f"exit={_resp.exit_code} (no local wallet — used Console JWT)"
                )
                return {
                    "exit_code": _resp.exit_code,
                    "stdout": _resp.stdout,
                    "stderr": _resp.stderr,
                    "duration_ms": int((time.monotonic() - _shell_start) * 1000),
                }
            except Exception as _console_err:  # noqa: BLE001
                _shell_errors.append(f"{type(_console_err).__name__}: {_console_err}")
        # Every account rejected it. Fall through to the CLI path, which will also fail —
        # but carrying both errors is strictly more than swallowing either.
        _console_failure = (
            f"[CONSOLE-SHELL] dseq={deployment_id} failed on all {len(_console_keys)} account(s): "
            f"{' | '.join(_shell_errors)[:1200]}"
        )
        logger.warning(f"{_console_failure}; falling back to provider-services lease-shell")

    # Use the OWNING wallet when we know it; fall back to "default" when we do not.
    #
    # An earlier revision of this change RAISED on a missing wallet_key_name, on the
    # reasoning that execing as a non-existent "default" produces an opaque provider
    # error. That broke `test_list_akash_pods_none_wallet_key_name`, which exists
    # because 500-ing on `wallet_key_name=None` was itself the bug fixed in #241/#242.
    # Raising here re-introduced it. The fallback stays.
    #
    # `wallet_key_name_defaulted` records that the owner was UNKNOWN and we queried as
    # "default" anyway — a guess about identity, which the provider reports as an
    # opaque error indistinguishable from a dead lease (#848). Stating it in the log is
    # what makes that distinguishable without changing behaviour.
    wallet_key_name = data.get("wallet_key_name") or "default"
    if not data.get("wallet_key_name"):
        logger.warning(
            f"Deployment {deployment_id} has no wallet_key_name — lease-shell will exec as "
            f"'default'. If that key is absent (wallet pool off, or a Console-owned "
            f"deployment) the provider answers with an opaque 'unknown error'."
        )
    if wallet_key_name.startswith("wallet-"):
        # Pool wallet — import the key into the local keyring if it is not already there.
        from handlers.logs import _ensure_pool_wallet_in_keyring

        imported = await _ensure_pool_wallet_in_keyring(wallet_key_name)
        if not imported:
            logger.warning(f"Could not import pool wallet {wallet_key_name} for lease-shell on DSEQ {deployment_id}")

    keyring_backend = os.environ.get("AKASH_KEYRING_BACKEND", "test")
    rpc_node = os.environ.get("AKASH_RPC_NODE") or os.environ.get("AKASH_NODE", "https://rpc.akashnet.net:443")

    # Build lease-shell command with "--" separator (REQUIRED for Go flag parser)
    cmd = [
        "provider-services",
        "lease-shell",
        f"--dseq={deployment_id}",
        f"--provider={provider}",
        "--from",
        wallet_key_name,
        f"--keyring-backend={keyring_backend}",
        f"--node={rpc_node}",
        "--",
        service_name,
    ] + command

    # Log the resolved invocation BEFORE running it.
    #
    # `provider-services` answers a failed lease-shell with one opaque line —
    # "Error: lease shell failed: the provider encountered an unknown error" — which is
    # the same string whether the key is missing, the service name does not exist in the
    # lease, or the lease itself is gone. It carries no signal about which. C1 (dfc)
    # burned an entire session on that ambiguity: five candidate causes were proposed and
    # eliminated one at a time because nothing recorded what was actually sent.
    #
    # These are identifiers, not secrets: a key NAME (the mnemonic lives in Secret
    # Manager), a DSEQ, a provider address, and the service name from the SDL. The
    # command itself is logged minus the trailing user command, which can carry payload.
    logger.info(
        f"[LEASE-SHELL] dseq={deployment_id} provider={provider} --from={wallet_key_name} "
        f"service={service_name} keyring={keyring_backend} node={rpc_node} "
        f"argv={' '.join(cmd[: len(cmd) - len(command)])}"
    )

    start = time.monotonic()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "duration_ms": duration_ms,
        }

    duration_ms = int((time.monotonic() - start) * 1000)

    # Strip provider-services WRN lines from stdout
    raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
    clean_stdout = "\n".join(line for line in raw_stdout.splitlines() if not line.startswith("WRN "))
    if clean_stdout and not clean_stdout.endswith("\n") and raw_stdout.endswith("\n"):
        clean_stdout += "\n"

    _stderr = stderr_bytes.decode("utf-8", errors="replace")

    # On failure, return the invocation ALONGSIDE the provider's reply.
    #
    # The `logger.info` above records this too, but the API pod's logs are not reachable
    # through `/v1/admin/logs/worker` — that endpoint hardcodes `container_name="worker"`.
    # A caller (the E2E suites) only ever sees this dict, and its `stderr` is what lands
    # in CI job logs. Without the context attached here, the only thing a failing run
    # shows is the provider's single opaque line, which is what made C1 (dfc) cost five
    # eliminated theories and five CI runs.
    if (process.returncode or 0) != 0:
        # Carry the Console-path failure too. It is logged above, but the API pod's logs
        # are unreachable (`/v1/admin/logs/worker` hardcodes container_name="worker"), so
        # without this the caller sees the CLI failure and has no idea the Console attempt
        # even happened, let alone why it failed. Same mistake as logging the invocation
        # only — fixed the same way.
        # PREPEND, do not append. Callers truncate stderr (the E2E prints a bounded
        # slice), so anything added at the END is the first thing cut — measured on run
        # 31324542572, where the Console error was sliced mid-word at "cannot es" and the
        # fields it exists to report never appeared. The provider's own line is the least
        # informative part here, so it goes last.
        _diag = (
            f"[LEASE-SHELL INVOCATION] dseq={deployment_id} provider={provider} "
            f"--from={wallet_key_name} (defaulted={not data.get('wallet_key_name')}) "
            f"service={service_name}"
        )
        if _console_failure:
            _diag = f"{_console_failure}\n{_diag}"
        _stderr = f"{_diag}\n{_stderr}"

    return {
        "exit_code": process.returncode or 0,
        "stdout": clean_stdout,
        "stderr": _stderr,
        "duration_ms": duration_ms,
    }


@contextlib.contextmanager
def _lat_vm_ssh(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    connect_timeout: int = 30,
    op: str = "operation",
):
    """Yield ``(ssh, vm_ip)`` — a connected root SSH client for the cluster's Latitude VM.

    Shared plumbing for the LAT exec and logs paths. LAT VMs run Docker
    containers started by cloud-init (``docker run -d --restart=always
    --name <svc>``); all container-level operations ride SSH.

    Requires:
      - ``latitude_vm_ip`` persisted in cluster metadata (added 2026-06-08)
      - ``LAT_SSH_PRIVATE_KEY`` env var / K8s secret with the matching private key
      - The matching public key injected into the VM's ``root`` authorized_keys
        at provision time (derived by ``clusters.py::_lat_ssh_public_key``,
        written via cloud-init in ``clusters.py::_build_lat_cloud_init``).

    Raises HTTPException 404 (cluster missing) or 502 (no IP / no key /
    auth / connect failure / any error from the caller's body, tagged ``op``).
    """
    import io
    import paramiko

    from services.entity_store_factory import get_entity_store

    registry = get_entity_store()
    cluster_data = registry.get_cluster(organization_id, project_id, cluster_id)
    if cluster_data is None:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
    metadata = cluster_data.get("metadata") or {}
    vm_ip = str(metadata.get("latitude_vm_ip") or "").strip()
    if not vm_ip:
        raise HTTPException(
            status_code=502,
            detail=f"Latitude VM has no IP recorded (cluster {cluster_id}) — "
            f"{op} unavailable until IP is populated after provisioning",
        )

    ssh_key_pem = os.environ.get("LAT_SSH_PRIVATE_KEY", "").strip()
    if not ssh_key_pem:
        raise HTTPException(
            status_code=502,
            detail="LAT_SSH_PRIVATE_KEY not configured — cannot SSH to Latitude VM",
        )

    try:
        # Load private key (support RSA and Ed25519)
        key_file = io.StringIO(ssh_key_pem)
        try:
            pkey = paramiko.Ed25519Key.from_private_key(key_file)
        except paramiko.SSHException:
            key_file.seek(0)
            pkey = paramiko.RSAKey.from_private_key(key_file)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=vm_ip,
                username="root",
                pkey=pkey,
                timeout=connect_timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            yield ssh, vm_ip
        finally:
            ssh.close()

    except HTTPException:
        raise
    except paramiko.AuthenticationException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"SSH auth failed for Latitude VM {vm_ip}: {exc}",
        )
    except paramiko.SSHException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"SSH connection failed to Latitude VM {vm_ip}: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Latitude VM {op} failed: {exc}",
        )


def _lat_find_container(ssh, vm_ip: str, container: Optional[str] = None) -> str:
    """Resolve the target Docker container id on a Latitude VM.

    With ``container`` given, filters by exact name (cloud-init names
    containers after their service, e.g. ``worker-postgres``). Without it,
    requires exactly one running container — ambiguity is a 400 asking the
    caller to disambiguate, never a silent ``--latest`` guess.
    """
    if container:
        find_cmd = "docker ps -q -f " + shlex.quote(f"name=^{container}$")
    else:
        find_cmd = "docker ps -q"
    _, find_out, _ = ssh.exec_command(find_cmd, timeout=10)
    ids = [line.strip() for line in (find_out.read().decode("utf-8", errors="replace") or "").splitlines() if line.strip()]

    if not ids:
        if container:
            raise HTTPException(
                status_code=502,
                detail=f"No running container named {container!r} on Latitude VM {vm_ip}",
            )
        raise HTTPException(
            status_code=502,
            detail=f"No running Docker container found on Latitude VM {vm_ip}",
        )
    if len(ids) > 1 and not container:
        raise HTTPException(
            status_code=400,
            detail=f"Multiple containers running on Latitude VM {vm_ip} — pass 'container' (the service name) to select one",
        )
    return ids[0]


# Dedicated bounded pool for LAT SSH work. Using the default to_thread
# executor risked starving UNRELATED to_thread users: stacked exec polls
# against an unresponsive VM each pin a thread for their full 30s connect
# timeout. A dedicated pool caps LAT SSH at 8 concurrent sessions — excess
# requests queue here (bounded by the client's own HTTP timeout) without
# touching the loop or the shared default executor.
_LAT_SSH_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="lat-ssh")


async def _run_in_lat_ssh_pool(fn, *args):
    return await asyncio.get_running_loop().run_in_executor(_LAT_SSH_EXECUTOR, functools.partial(fn, *args))


# Container-readiness states for a LAT VM, distinguishing the network/infra
# layer from the workload layer so callers can react differently:
#   "running"      — SSH ok AND a workload container is up (the ready state)
#   "no_container" — SSH ok but `docker ps` empty (workload down: booting,
#                    crashed, or mid-restart) → a REAL recovery/workload failure
#   "unreachable"  — SSH connect refused/timed out across all attempts. VM may
#                    be mid-reboot, or its IP went dead (the Latitude IP flake,
#                    which can onset mid-life). INFRA transient, not our code —
#                    callers may treat a prolonged unreachable as a provider
#                    skip rather than a hard failure.
#   "unknown"      — cannot check (no LAT_SSH_PRIVATE_KEY / paramiko).
LAT_CONTAINER_RUNNING = "running"
LAT_CONTAINER_NONE = "no_container"
LAT_VM_UNREACHABLE = "unreachable"
LAT_CONTAINER_UNKNOWN = "unknown"


def _lat_container_status_sync(vm_ip: str, connect_timeout: int = 5, attempts: int = 3) -> str:
    """Best-effort container probe returning one of the LAT_CONTAINER_* states.

    Never raises — this feeds a polled readiness signal, so a transient blip
    must not 502. Distinguishing "unreachable" (SSH connect failed = infra/IP
    flake) from "no_container" (SSH ok, nothing running = workload down) lets the
    recovery tests treat the Latitude IP flake as a neutral skip while a
    genuinely down container stays a hard failure.

    Probed with a short RETRY (carried from the pre-split de-flake): a single
    ``docker ps`` over SSH is noisy — a transient connect/exec blip on an
    otherwise-healthy VM read as down and flapped the pod Running→Pending 4s
    after recovery (failed C0-lat phase 6). A ``--restart=always`` container
    that is genuinely up is seen within a couple of probes, so we return RUNNING
    on first sight and only conclude NONE after the container is consistently
    ABSENT across attempts WHILE SSH worked; if SSH never connected at all we
    return UNREACHABLE (infra), distinct from a crashed-workload NONE.
    """
    import io

    pem = os.environ.get("LAT_SSH_PRIVATE_KEY", "").strip()
    if not pem or not vm_ip:
        return LAT_CONTAINER_UNKNOWN
    try:
        import paramiko
    except ImportError:
        return LAT_CONTAINER_UNKNOWN

    key_file = io.StringIO(pem)
    pkey = None
    for loader in (paramiko.Ed25519Key, paramiko.RSAKey):
        try:
            key_file.seek(0)
            pkey = loader.from_private_key(key_file)
            break
        except paramiko.SSHException:
            continue
    if pkey is None:
        return LAT_CONTAINER_UNKNOWN

    saw_ssh = False
    for attempt in range(attempts):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=vm_ip,
                username="root",
                pkey=pkey,
                timeout=connect_timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            saw_ssh = True
            _, out, _ = ssh.exec_command("docker ps -q", timeout=10)
            if (out.read().decode("utf-8", errors="replace") or "").strip():
                return LAT_CONTAINER_RUNNING  # container up — done, no need to retry
        except Exception:
            # connect refused/timed out (sshd not up / IP flake) or exec blip — retry.
            pass
        finally:
            ssh.close()
        if attempt < attempts - 1:
            time.sleep(1.5)

    # Exhausted. SSH connected at least once but the container was never seen →
    # workload genuinely down (NONE). SSH NEVER connected → infra/IP flake
    # (UNREACHABLE), distinct from a crashed workload so callers can skip-neutral
    # on a prolonged unreachable instead of hard-failing recovery.
    return LAT_CONTAINER_NONE if saw_ssh else LAT_VM_UNREACHABLE


def _lat_container_running_sync(vm_ip: str, connect_timeout: int = 8) -> Optional[bool]:
    """Backward-compatible bool wrapper over ``_lat_container_status_sync``.

    True = running, False = reachable-but-no-container, None = can't determine
    (no key) OR unreachable (so callers that only branch on False/None keep the
    previous "not-ready, keep polling" behavior for the unreachable case).
    """
    status = _lat_container_status_sync(vm_ip, connect_timeout)
    if status == LAT_CONTAINER_RUNNING:
        return True
    if status == LAT_CONTAINER_NONE:
        return False
    return None


async def _exec_lat_deployment(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
    command: List[str],
    timeout: int,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a command in a LAT (Latitude) VM workload via SSH + docker exec.

    The paramiko work runs in the bounded LAT SSH pool: a sync SSH connect
    to an unresponsive VM (e.g. mid-reboot during C1 recovery) blocks its
    thread for the full timeout; running it inline on the event loop starved
    the loop so hard that even /health/live stopped answering and kubelet
    killed the API — both canary replicas died in lockstep during C1-lat
    phase 7 (2026-06-12).
    """
    return await _run_in_lat_ssh_pool(
        _exec_lat_deployment_sync,
        organization_id,
        project_id,
        cluster_id,
        resource_id,
        command,
        timeout,
        container,
    )


def _exec_lat_deployment_sync(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
    command: List[str],
    timeout: int,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.monotonic()
    with _lat_vm_ssh(organization_id, project_id, cluster_id, connect_timeout=min(timeout, 30), op="exec") as (ssh, vm_ip):
        container_id = _lat_find_container(ssh, vm_ip, container)

        # Build docker exec command. The string goes through the VM's
        # login shell, so every argv element must be shell-quoted or
        # SQL/scripts with (, ', ; etc. get re-parsed by bash — quoting
        # preserves the argv boundaries the other providers get for free
        # from the k8s exec API.
        cmd_str = " ".join(shlex.quote(arg) for arg in command)
        docker_cmd = f"docker exec {shlex.quote(container_id)} {cmd_str}"

        _, stdout, stderr = ssh.exec_command(docker_cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        stdout_str = stdout.read().decode("utf-8", errors="replace")
        stderr_str = stderr.read().decode("utf-8", errors="replace")

    duration_ms = int((time.monotonic() - start) * 1000)
    return {
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "duration_ms": duration_ms,
    }


async def _get_lat_deployment_logs(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
    tail: int,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """Get container logs from a LAT (Latitude) VM workload via SSH + docker logs.

    ``docker logs`` interleaves the app's stdout and stderr; both are merged
    into ``logs`` (2>&1) for parity with ``kubectl logs``. The ``previous``
    flag has no LAT analogue — ``--restart=always`` restarts the SAME
    container, so its log stream already spans restarts.

    Runs in the bounded LAT SSH pool for the same event-loop-blocking reason
    as ``_exec_lat_deployment``.
    """
    return await _run_in_lat_ssh_pool(
        _get_lat_deployment_logs_sync,
        organization_id,
        project_id,
        cluster_id,
        resource_id,
        tail,
        container,
    )


def _get_lat_deployment_logs_sync(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    resource_id: str,
    tail: int,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.monotonic()
    with _lat_vm_ssh(organization_id, project_id, cluster_id, op="logs") as (ssh, vm_ip):
        container_id = _lat_find_container(ssh, vm_ip, container)

        logs_cmd = f"docker logs --tail {int(tail)} {shlex.quote(container_id)} 2>&1"
        _, stdout, _ = ssh.exec_command(logs_cmd, timeout=30)
        exit_code = stdout.channel.recv_exit_status()
        logs = stdout.read().decode("utf-8", errors="replace")

        if exit_code != 0:
            raise HTTPException(
                status_code=502,
                detail=f"docker logs failed on Latitude VM {vm_ip} (exit {exit_code}): {logs[:500]}",
            )

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "[%s] Retrieved logs for LAT workload %s (%d lines, %dms)",
        organization_id,
        resource_id,
        len(logs.splitlines()),
        duration_ms,
    )
    return {
        "workload_id": f"lat-{resource_id}",
        "logs": logs,
        "lines": len(logs.splitlines()),
        "tail": tail,
        "container": container,
    }


# =============================================================================
# Scale Workload (Unified)
# =============================================================================


class ScaleWorkloadRequest(BaseModel):
    replicas: int = Field(..., ge=0, le=100, description="Target replica count")


@workloads_router.post(
    "/{workload_id}/scale",
    summary="Scale a workload",
    description="""
Scale a workload to a specific replica count.

**GKE:** Updates the Deployment replica count via Kubernetes API.

**Akash/DFC:** Returns 400 (scaling not supported - redeploy with updated SDL manifest).

**CronJob:** Returns 400 (not applicable).
""",
)
async def scale_workload(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    request: ScaleWorkloadRequest,
    organization: Dict = Depends(get_current_organization),
):
    """Scale a workload to a specific replica count."""
    logger.info(f"[{organization_id}] Scale workload: {workload_id} to {request.replicas} replicas")

    workload_type, resource_id = _parse_workload_id(workload_id)

    if workload_type == "gke_worker":
        return await _scale_gke_worker(organization_id, cluster_id, resource_id, request.replicas)
    elif workload_type == "akash_deployment":
        raise HTTPException(
            status_code=400,
            detail="Scaling is not supported for Akash/DFC deployments. Akash deployments must be redeployed with updated replica count in the SDL manifest.",
        )
    elif workload_type == "cronjob":
        raise HTTPException(status_code=400, detail="Scaling is not applicable to CronJob workloads")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")


async def _scale_gke_worker(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
    replicas: int,
) -> Dict[str, Any]:
    """Scale a GKE worker deployment to a specific replica count."""
    db = await _get_firestore_client(firestore)

    # Look up worker in Firestore (gke_deployments first, workers legacy fallback)
    data = _resolve_gke_worker(db, organization_id, cluster_id, worker_id)
    namespace = data.get("namespace", f"c-{cluster_id}")

    try:
        v1 = k8s_client.AppsV1Api()
        v1.patch_namespaced_deployment(
            name=f"worker-{worker_id}",
            namespace=namespace,
            body={"spec": {"replicas": replicas}},
        )
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Deployment not found")
        raise HTTPException(status_code=e.status or 500, detail=f"K8s API error: {e.reason}")

    logger.info(f"[{organization_id}] Scaled GKE worker {worker_id} to {replicas} replicas")
    return {
        "workload_id": f"worker-{worker_id}",
        "replicas": replicas,
        "status": "scaled",
    }


# =============================================================================
# Logs Workload (Unified)
# =============================================================================


@workloads_router.get(
    "/{workload_id}/logs",
    summary="Get workload container logs",
    description="""
Retrieve container logs from a workload.

**GKE:** Uses kubectl logs subprocess with tail, container, and previous container support.

**Akash/DFC:** Uses provider-services lease-logs subprocess.

**CronJob:** Returns 400 (not applicable).
""",
)
async def get_workload_logs(
    organization_id: str,
    project_id: str,
    cluster_id: str,
    workload_id: str,
    tail: int = Query(100, ge=1, le=10000, description="Number of lines to return"),
    container: Optional[str] = Query(
        None, description="Container name (GKE and LAT; for LAT it is the docker --name, i.e. the service name)"
    ),
    previous: bool = Query(False, description="Return logs from previous container instance"),
    organization: Dict = Depends(get_current_organization),
):
    """Get container logs from a workload."""
    logger.info(f"[{organization_id}] Get logs for workload: {workload_id}")

    workload_type, resource_id = _parse_workload_id(workload_id)

    if workload_type == "gke_worker":
        return await _get_gke_worker_logs(organization_id, cluster_id, resource_id, tail, container, previous)
    elif workload_type == "akash_deployment":
        return await _get_akash_deployment_logs(organization_id, cluster_id, resource_id, tail)
    elif workload_type == "lat_deployment":
        return await _get_lat_deployment_logs(organization_id, project_id, cluster_id, resource_id, tail, container)
    elif workload_type == "cronjob":
        raise HTTPException(status_code=400, detail="Logs are not applicable to CronJob workloads")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workload type: {workload_type}")


async def _get_gke_worker_logs(
    organization_id: str,
    cluster_id: str,
    worker_id: str,
    tail: int,
    container: Optional[str],
    previous: bool,
) -> Dict[str, Any]:
    """Get logs from a GKE worker pod via kubectl subprocess."""
    db = await _get_firestore_client(firestore)

    # Look up worker in Firestore (gke_deployments first, workers legacy fallback)
    data = _resolve_gke_worker(db, organization_id, cluster_id, worker_id)
    namespace = data.get("namespace", f"c-{cluster_id}")

    # Derive pod name (StatefulSet convention)
    pod_name = f"worker-{worker_id}-0"

    # Build kubectl logs command
    cmd = ["kubectl", "logs", pod_name, "-n", namespace, f"--tail={tail}"]
    if container:
        cmd.extend(["-c", container])
    if previous:
        cmd.append("--previous")

    start = time.monotonic()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError:
        process.kill()
        raise HTTPException(status_code=504, detail="Log retrieval timed out")

    if process.returncode != 0:
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {stderr}")

    duration_ms = int((time.monotonic() - start) * 1000)
    logs = stdout_bytes.decode("utf-8", errors="replace")

    logger.info(f"[{organization_id}] Retrieved logs for GKE worker {worker_id} ({len(logs.splitlines())} lines)")
    return {
        "workload_id": f"worker-{worker_id}",
        "logs": logs,
        "lines": len(logs.splitlines()),
        "tail": tail,
        "container": container,
    }


async def _get_akash_deployment_logs(
    organization_id: str,
    cluster_id: str,
    deployment_id: str,
    tail: int,
) -> Dict[str, Any]:
    """Get logs from an Akash/DFC deployment via lease-logs subprocess."""
    db = await _get_firestore_client(firestore)

    doc = db.collection("akash_deployments").document(deployment_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    data = doc.to_dict()

    # Verify ownership
    if data.get("organization_id") != organization_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")
    if data.get("cluster_id") != cluster_id:
        raise HTTPException(status_code=404, detail=f"Workload akash-{deployment_id} not found")

    status = data.get("status")
    if status not in ("active", "leased"):
        raise HTTPException(status_code=400, detail="Deployment is not active")

    provider = data.get("provider_address")
    if not provider:
        raise HTTPException(status_code=500, detail="Deployment has no provider address")

    service_name = data.get("service_name") or data.get("worker_id")
    if not service_name:
        raise HTTPException(status_code=500, detail="Could not determine service name")

    keyring_backend = os.environ.get("AKASH_KEYRING_BACKEND", "test")
    rpc_node = os.environ.get("AKASH_RPC_NODE") or os.environ.get("AKASH_NODE", "https://rpc.akashnet.net:443")

    cmd = [
        "provider-services",
        "lease-logs",
        f"--dseq={deployment_id}",
        f"--provider={provider}",
        "--from",
        "default",
        f"--keyring-backend={keyring_backend}",
        f"--node={rpc_node}",
        f"--tail={tail}",
        "--follow=false",
        f"--service={service_name}",
    ]

    start = time.monotonic()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError:
        process.kill()
        raise HTTPException(status_code=504, detail="Log retrieval timed out")

    if process.returncode != 0:
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {stderr}")

    duration_ms = int((time.monotonic() - start) * 1000)

    # Strip provider-services WRN lines from stdout
    raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
    clean_stdout = "\n".join(line for line in raw_stdout.splitlines() if not line.startswith("WRN "))
    if clean_stdout and not clean_stdout.endswith("\n") and raw_stdout.endswith("\n"):
        clean_stdout += "\n"

    logger.info(
        f"[{organization_id}] Retrieved logs for Akash deployment {deployment_id} ({len(clean_stdout.splitlines())} lines)"
    )
    return {
        "workload_id": f"akash-{deployment_id}",
        "logs": clean_stdout,
        "lines": len(clean_stdout.splitlines()),
        "tail": tail,
    }
