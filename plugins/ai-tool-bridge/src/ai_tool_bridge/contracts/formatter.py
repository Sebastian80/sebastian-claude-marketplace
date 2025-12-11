"""
Formatter Protocol - Contract for output formatters.

Formatters transform data into different output formats:
- json: Raw JSON for parsing
- human: Colored, tabular output for terminals
- ai: Structured output optimized for LLM consumption
- markdown: Markdown tables and formatting
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FormatterProtocol(Protocol):
    """Contract for output formatters.

    Implementations transform arbitrary data into formatted strings.

    Example:
        class HumanFormatter:
            @property
            def name(self) -> str:
                return "human"

            def format(self, data: Any) -> str:
                # Return colored, tabular output
                ...
    """

    @property
    def name(self) -> str:
        """Formatter identifier.

        Used for registration and lookup. Common names:
        - 'json': Raw JSON
        - 'human': Terminal-friendly with colors
        - 'ai': Optimized for LLM consumption
        - 'markdown': Markdown tables
        """
        ...

    @property
    def content_type(self) -> str:
        """MIME type for HTTP response.

        Examples:
        - 'application/json' for json formatter
        - 'text/plain' for human, ai formatters
        - 'text/markdown' for markdown formatter
        """
        ...

    def format(self, data: Any) -> str:
        """Format data to string output.

        Args:
            data: Any data structure (dict, list, str, etc.)

        Returns:
            Formatted string representation
        """
        ...

    def format_error(self, error: str, hint: str | None = None) -> str:
        """Format error message.

        Args:
            error: Error message
            hint: Optional hint for resolution

        Returns:
            Formatted error string
        """
        ...

    def format_list(self, items: list[Any], item_type: str | None = None) -> str:
        """Format a list of items.

        Args:
            items: List of items to format
            item_type: Optional type hint (e.g., 'issues', 'projects')

        Returns:
            Formatted list representation
        """
        ...
