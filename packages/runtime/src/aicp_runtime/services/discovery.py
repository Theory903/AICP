"""Discovery service for runtime responses."""

from __future__ import annotations

import re
from typing import Any

from aicp import __version__
from aicp.interfaces.capability_provider import CapabilityProvider


class DiscoveryService:
    """Build discovery payloads from a capability provider."""

    _QUERY_INTENT_TERMS = {
        "query": {
            "check",
            "describe",
            "details",
            "fetch",
            "find",
            "get",
            "list",
            "lookup",
            "read",
            "retrieve",
            "search",
            "show",
            "status",
            "view",
        },
        "action": {
            "add",
            "approve",
            "archive",
            "cancel",
            "create",
            "delete",
            "deploy",
            "export",
            "mark",
            "remove",
            "run",
            "send",
            "submit",
            "sync",
            "transfer",
            "update",
            "write",
        },
    }
    _STOP_TERMS = {
        "a",
        "an",
        "and",
        "for",
        "in",
        "of",
        "the",
        "to",
        "with",
    }

    def __init__(self, capability_provider: CapabilityProvider):
        self._provider = capability_provider

    async def discover(self) -> dict[str, Any]:
        """Return a normalized discovery document."""
        capabilities = await self._provider.discover()
        sorted_capabilities = sorted(capabilities, key=lambda cap: cap.name)
        serialized_capabilities = [
            self._serialize_capability(capability) for capability in sorted_capabilities
        ]
        graph = self._build_graph(sorted_capabilities)

        return {
            "protocol": "aicp",
            "version": __version__,
            "capabilities": serialized_capabilities,
            "graph": graph,
            "metadata": {
                "provider_name": self._provider.provider_name,
                "provider_type": self._provider.provider_type,
                "capability_count": len(serialized_capabilities),
            },
            "links": {
                "self": "/.well-known/aicp",
            },
        }

    async def rank_capabilities(
        self,
        *,
        query: str = "",
        session: dict[str, Any] | None = None,
        interaction: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        capabilities = await self._provider.discover()
        sorted_capabilities = sorted(capabilities, key=lambda cap: cap.name)
        graph = self._build_graph(sorted_capabilities)
        last_capability = str((interaction or {}).get("last_capability") or "").strip()
        session_provider = str((session or {}).get("provider_name") or "").strip()
        ranked: list[dict[str, Any]] = []

        semantic_scores: dict[str, float] = {}
        if query.strip():
            semantic_scores = await self._compute_semantic_similarity(
                query=query.strip(),
                capabilities=sorted_capabilities,
            )

        for capability in sorted_capabilities:
            score, reasons = self._score_capability(
                capability,
                query=query,
                graph=graph,
                last_capability=last_capability,
                session_provider=session_provider,
            )

            capability_name = str(getattr(capability, "name", "")).strip()
            semantic_score = semantic_scores.get(capability_name, 0.0)
            if semantic_score > 0:
                score += int(semantic_score * 30)
                self._append_reason(reasons, "semantic:embedding_match")

            ranked.append(
                {
                    "capability": self._serialize_capability(capability),
                    "score": score,
                    "reasons": reasons,
                }
            )

        ranked.sort(
            key=lambda item: (-item["score"], item["capability"]["name"])
        )
        return ranked[: max(limit, 0)]

    async def _compute_semantic_similarity(
        self,
        query: str,
        capabilities: list[Any],
    ) -> dict[str, float]:
        """Compute semantic similarity scores for capability matching.

        This is a lightweight implementation that uses keyword co-occurrence.
        Can be extended with embedding-based semantic search in the future.
        """
        query_terms = self._extract_terms(query.lower())
        scores: dict[str, float] = {}

        for capability in capabilities:
            capability_name = str(getattr(capability, "name", "")).strip()
            description = str(getattr(capability, "description", "") or "").lower()
            tags = [str(tag).lower() for tag in getattr(capability, "tags", []) or []]

            name_terms = self._extract_terms(capability_name)
            desc_terms = self._extract_terms(description)
            tag_terms: set[str] = set()
            for tag in tags:
                tag_terms.update(self._extract_terms(tag))

            term_union = query_terms & name_terms
            term_union |= query_terms & desc_terms
            term_union |= query_terms & tag_terms

            if term_union:
                scores[capability_name] = min(len(term_union) / max(len(query_terms), 1), 1.0)

        return scores

    def _serialize_capability(self, capability: Any) -> dict[str, Any]:
        """Serialize a capability into a JSON-safe discovery record."""
        model_dump = getattr(capability, "model_dump", None)
        if callable(model_dump):
            data = model_dump(exclude_none=True, mode="json")
            if isinstance(data, dict):
                return data

        raise ValueError(
            f"Capability {getattr(capability, 'name', '<unknown>')} is not serializable"
        )

    def _build_graph(self, capabilities: list[Any]) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        node_ids: set[str] = set()
        edge_keys: set[tuple[str, str, str]] = set()

        for capability in capabilities:
            capability_id = str(getattr(capability, "name", "")).strip()
            if not capability_id:
                continue

            self._add_node(
                nodes,
                node_ids,
                {
                    "id": capability_id,
                    "type": "capability",
                    "name": capability_id,
                    "kind": getattr(getattr(capability, "kind", None), "value", None)
                    or str(getattr(capability, "kind", "")),
                    "provider_name": getattr(
                        getattr(capability, "provider", None),
                        "name",
                        None,
                    ),
                    "risk": getattr(capability, "risk", None),
                },
            )

            continuation = getattr(capability, "continuation", None)
            if continuation is not None:
                for next_capability in getattr(continuation, "next_capabilities", []) or []:
                    self._add_capability_edge(
                        nodes,
                        node_ids,
                        edges,
                        edge_keys,
                        source=capability_id,
                        target=next_capability,
                        edge_type="continuation",
                        metadata={"hint": getattr(continuation, "next_hint", None)},
                    )

            for dependency in getattr(capability, "dependency_capabilities", []) or []:
                self._add_capability_edge(
                    nodes,
                    node_ids,
                    edges,
                    edge_keys,
                    source=capability_id,
                    target=dependency,
                    edge_type="dependency",
                )

            for next_candidate in getattr(capability, "often_follows", []) or []:
                self._add_capability_edge(
                    nodes,
                    node_ids,
                    edges,
                    edge_keys,
                    source=capability_id,
                    target=next_candidate,
                    edge_type="often_follows",
                )

            rollback_capability = getattr(capability, "rollback_capability", None)
            if rollback_capability:
                self._add_capability_edge(
                    nodes,
                    node_ids,
                    edges,
                    edge_keys,
                    source=capability_id,
                    target=rollback_capability,
                    edge_type="compensation",
                )

            auth_requirement = getattr(capability, "auth", None)
            if auth_requirement is not None and getattr(
                auth_requirement, "requires_session", False
            ):
                provider_name = str(
                    getattr(auth_requirement, "required_session_provider", None)
                    or getattr(getattr(capability, "provider", None), "name", None)
                    or "default"
                ).strip()
                session_node_id = f"session:{provider_name}"
                self._add_node(
                    nodes,
                    node_ids,
                    {
                        "id": session_node_id,
                        "type": "session_requirement",
                        "provider_name": provider_name,
                        "auth_mode": getattr(auth_requirement, "mode", None),
                    },
                )
                self._add_edge(
                    edges,
                    edge_keys,
                    {
                        "source": capability_id,
                        "target": session_node_id,
                        "type": "requires_session",
                        "metadata": {
                            "csrf_required": bool(
                                getattr(auth_requirement, "csrf_required", False)
                            ),
                        },
                    },
                )

            if self._is_approval_candidate(capability):
                approval_node_id = "approval:human_review"
                self._add_node(
                    nodes,
                    node_ids,
                    {
                        "id": approval_node_id,
                        "type": "approval_requirement",
                        "name": "human_review",
                    },
                )
                self._add_edge(
                    edges,
                    edge_keys,
                    {
                        "source": capability_id,
                        "target": approval_node_id,
                        "type": "requires_approval",
                        "metadata": {
                            "policy": getattr(
                                getattr(capability, "policy", None),
                                "policy_name",
                                None,
                            ),
                        },
                    },
                )

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        }

    def _score_capability(
        self,
        capability: Any,
        *,
        query: str,
        graph: dict[str, Any],
        last_capability: str,
        session_provider: str,
    ) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        normalized_query = query.strip().lower()
        capability_name = str(getattr(capability, "name", "")).strip()
        description = str(getattr(capability, "description", "") or "")
        tags = [str(tag).strip().lower() for tag in getattr(capability, "tags", []) or []]
        query_terms = self._extract_terms(normalized_query)
        name_terms = self._extract_terms(capability_name)
        description_terms = self._extract_terms(description)
        tag_terms: set[str] = set()
        for tag in tags:
            tag_terms.update(self._extract_terms(tag))

        if normalized_query:
            name_lower = capability_name.lower()
            description_lower = description.lower()
            if name_lower == normalized_query:
                score += 120
                self._append_reason(reasons, "query:exact_name")
            elif name_lower.startswith(normalized_query):
                score += 75
                self._append_reason(reasons, "query:name_prefix")
            elif normalized_query in name_lower:
                score += 50
                self._append_reason(reasons, "query:name_contains")

            if normalized_query in description_lower:
                score += 16
                self._append_reason(reasons, "query:description_terms")

            if any(normalized_query in tag for tag in tags):
                score += 14
                self._append_reason(reasons, "query:tag_match")

            name_overlap = query_terms.intersection(name_terms)
            if name_overlap:
                score += 14 + (len(name_overlap) * 9)
                self._append_reason(reasons, "query:name_contains")

            description_overlap = query_terms.intersection(description_terms)
            if description_overlap:
                score += len(description_overlap) * 7
                self._append_reason(reasons, "query:description_terms")

            tag_overlap = query_terms.intersection(tag_terms)
            if tag_overlap:
                score += 10 + (len(tag_overlap) * 6)
                self._append_reason(reasons, "query:tag_match")

            kind_intent = self._infer_query_intent(query_terms)
            capability_kind = self._normalize_capability_kind(capability)
            if kind_intent == "query" and capability_kind == "query":
                score += 12
                self._append_reason(reasons, "kind:query_match")
            elif kind_intent == "action" and capability_kind in {
                "action",
                "async_action",
                "batch_action",
                "workflow",
            }:
                score += 12
                self._append_reason(reasons, "kind:action_match")

        auth_requirement = getattr(capability, "auth", None)
        if auth_requirement is not None and getattr(auth_requirement, "requires_session", False):
            required_provider = str(
                getattr(auth_requirement, "required_session_provider", None)
                or getattr(getattr(capability, "provider", None), "name", None)
                or ""
            ).strip()
            if session_provider and required_provider and required_provider == session_provider:
                score += 24
                self._append_reason(reasons, "auth:session_compatible")
            elif session_provider and required_provider and required_provider != session_provider:
                score -= 12
                self._append_reason(reasons, "auth:session_incompatible")
            elif not session_provider:
                score -= 18
                self._append_reason(reasons, "auth:session_missing")

        if last_capability:
            for edge in graph.get("edges", []):
                if edge.get("source") != last_capability or edge.get("target") != capability_name:
                    continue
                edge_type = str(edge.get("type") or "")
                if edge_type == "continuation":
                    score += 45
                elif edge_type == "often_follows":
                    score += 30
                elif edge_type == "dependency":
                    score += 18
                self._append_reason(reasons, f"graph:{edge_type}")

        risk = getattr(capability, "risk", None)
        if risk == "low":
            score += 5
            self._append_reason(reasons, "risk:low")
        elif risk == "medium":
            score += 2
            self._append_reason(reasons, "risk:medium")
        elif risk == "critical":
            score -= 5
            self._append_reason(reasons, "risk:critical")

        return score, reasons

    def _append_reason(self, reasons: list[str], reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    def _normalize_capability_kind(self, capability: Any) -> str:
        kind = getattr(capability, "kind", None)
        return str(getattr(kind, "value", kind) or "").strip().lower()

    def _infer_query_intent(self, query_terms: set[str]) -> str | None:
        if not query_terms:
            return None

        query_matches = len(query_terms.intersection(self._QUERY_INTENT_TERMS["query"]))
        action_matches = len(query_terms.intersection(self._QUERY_INTENT_TERMS["action"]))
        if query_matches == action_matches == 0:
            return None
        if query_matches >= action_matches:
            return "query"
        return "action"

    def _extract_terms(self, value: str) -> set[str]:
        tokens = [token for token in re.split(r"[^a-z0-9]+", value.lower()) if token]
        terms: set[str] = set()
        for token in tokens:
            if token in self._STOP_TERMS:
                continue
            terms.update(self._term_variants(token))
        return terms

    def _term_variants(self, token: str) -> set[str]:
        variants = {token}
        if len(token) <= 3:
            return variants

        if token.endswith("ies") and len(token) > 4:
            variants.add(f"{token[:-3]}y")
        if token.endswith("ing") and len(token) > 5:
            base = token[:-3]
            variants.add(base)
            variants.add(f"{base}e")
        if token.endswith("ed") and len(token) > 4:
            base = token[:-2]
            variants.add(base)
            variants.add(f"{base}e")
        if token.endswith("es") and len(token) > 4:
            variants.add(token[:-2])
        if token.endswith("s") and len(token) > 3:
            variants.add(token[:-1])
        return {variant for variant in variants if variant}

    def _is_approval_candidate(self, capability: Any) -> bool:
        if getattr(capability, "policy", None) is not None:
            return True

        tags = [str(tag).strip().lower() for tag in getattr(capability, "tags", []) or []]
        if any(tag in {"destructive", "governance:approval_candidate"} for tag in tags):
            return True

        return bool(getattr(capability, "is_destructive", False))

    def _add_node(
        self,
        nodes: list[dict[str, Any]],
        node_ids: set[str],
        node: dict[str, Any],
    ) -> None:
        node_id = str(node.get("id") or "").strip()
        if not node_id or node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(node)

    def _add_edge(
        self,
        edges: list[dict[str, Any]],
        edge_keys: set[tuple[str, str, str]],
        edge: dict[str, Any],
    ) -> None:
        source = str(edge.get("source") or "").strip()
        target = str(edge.get("target") or "").strip()
        edge_type = str(edge.get("type") or "").strip()
        key = (source, target, edge_type)
        if not source or not target or not edge_type or key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(edge)

    def _add_capability_edge(
        self,
        nodes: list[dict[str, Any]],
        node_ids: set[str],
        edges: list[dict[str, Any]],
        edge_keys: set[tuple[str, str, str]],
        *,
        source: str,
        target: str,
        edge_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        target_id = str(target).strip()
        if not target_id:
            return

        self._add_node(
            nodes,
            node_ids,
            {
                "id": target_id,
                "type": "capability",
                "name": target_id,
            },
        )
        self._add_edge(
            edges,
            edge_keys,
            {
                "source": source,
                "target": target_id,
                "type": edge_type,
                "metadata": metadata or {},
            },
        )
