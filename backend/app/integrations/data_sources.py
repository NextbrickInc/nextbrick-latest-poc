"""
Unified data source connector interfaces and stubs.

This module provides lightweight, open-source–friendly connector classes for
all major systems the Keysight AI Assistant can integrate with:

- Coveo
- AEM DAM
- AEM Pages
- Confluence
- Salesforce (cases, emails, KB, service notes, service orders)
- PIM
- Skilljar LMS
- Oracle (parts and sales data)
- Snowflake (enterprise data warehouse)

Each connector exposes a minimal, common shape so higher-level orchestration
code can treat them uniformly while allowing system-specific capabilities.

Real credentials and secure client wiring should be provided via environment
variables in `app.config.Settings` and injected here when you are ready to
connect to production systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, runtime_checkable

from app.config import settings


@runtime_checkable
class SearchableDataSource(Protocol):
    """Minimal capability for any searchable external system."""

    name: str

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """Run a search query and return normalized records."""


@dataclass
class CoveoConnector:
    name: str = "Coveo"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Implement REST call to Coveo Search API using API key / org ID.
        return []


@dataclass
class AemDamConnector:
    name: str = "AEM DAM"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Query AEM Assets (DAM) via GraphQL or Assets HTTP API.
        return []


@dataclass
class AemPagesConnector:
    name: str = "AEM Pages"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Query AEM Sites content (pages, experience fragments) via API.
        return []


@dataclass
class ConfluenceConnector:
    name: str = "Confluence"
    base_url: Optional[str] = settings.confluence_url

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # Existing tools use Atlassian REST API; this stub mirrors that shape.
        return []


@dataclass
class SalesforceConnector:
    """
    Aggregated Salesforce connector.

    Intended to cover:
    - Cases
    - Case emails
    - Knowledge Base articles
    - Service notes
    - Service orders
    """

    name: str = "Salesforce"
    api_base_url: Optional[str] = settings.sf_api_base_url

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # Delegate to existing Salesforce tools (SOQL / REST) when wired.
        return []


@dataclass
class PimConnector:
    name: str = "PIM"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Implement product information search (specs, hierarchy, pricing).
        return []


@dataclass
class SkilljarConnector:
    name: str = "Skilljar LMS"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Integrate with Skilljar REST API for courses, paths, and labs.
        return []


@dataclass
class OracleConnector:
    """
    Oracle connector for parts and sales data.
    """

    name: str = "Oracle"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Implement Oracle DB / cloud query (parts, pricing, orders).
        return []


@dataclass
class SnowflakeConnector:
    """
    Snowflake connector for enterprise data warehouse analytics.
    """

    name: str = "Snowflake"

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # TODO: Implement Snowflake query using Python connector.
        return []


def all_data_source_connectors() -> Iterable[SearchableDataSource]:
    """
    Convenience factory returning all known data source connectors.

    Higher-level orchestration (e.g. LangGraph tools) can iterate this
    collection and route queries to one or more backends as needed.
    """

    return (
        CoveoConnector(),
        AemDamConnector(),
        AemPagesConnector(),
        ConfluenceConnector(),
        SalesforceConnector(),
        PimConnector(),
        SkilljarConnector(),
        OracleConnector(),
        SnowflakeConnector(),
    )

