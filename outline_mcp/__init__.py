"""outline-mcp: Read-only MCP server for Outline wiki"""

__version__ = "1.0.0"

from .client import Client, parse_doc_ref
from .types import Result

__all__ = ["Client", "parse_doc_ref", "Result"]
