"""
Formatter Registry - Manages output formatters.

Formatters transform data into different output formats.
The registry supports both:
- Global formatters (any data type)
- Plugin-specific formatters (plugin + data_type combination)

Lookup order:
1. Plugin-specific formatter: (plugin, data_type, format)
2. Global formatter: (format)
3. Fallback to JSON
"""

from typing import Any, Callable

from ..contracts import FormatterProtocol


# Type alias for formatter factory functions
FormatterFactory = Callable[[], FormatterProtocol]


class FormatterRegistry:
    """Registry for output formatters.

    Example:
        registry = FormatterRegistry()

        # Register global formatter
        registry.register_global("human", HumanFormatter)

        # Register plugin-specific formatter
        registry.register("jira", "issue", "human", JiraIssueHumanFormatter)

        # Format data
        output = registry.format(data, "human", plugin="jira", data_type="issue")
    """

    def __init__(self) -> None:
        # Global formatters: format_name -> FormatterProtocol
        self._global: dict[str, FormatterProtocol] = {}

        # Plugin-specific formatters: (plugin, data_type, format) -> FormatterProtocol
        self._specific: dict[tuple[str, str, str], FormatterProtocol] = {}

    def register_global(self, format_name: str, formatter: FormatterProtocol) -> None:
        """Register a global formatter.

        Args:
            format_name: Format identifier (e.g., 'json', 'human', 'ai')
            formatter: Formatter instance implementing FormatterProtocol
        """
        self._global[format_name] = formatter

    def register(
        self,
        plugin: str,
        data_type: str,
        format_name: str,
        formatter: FormatterProtocol,
    ) -> None:
        """Register a plugin-specific formatter.

        Args:
            plugin: Plugin name (e.g., 'jira')
            data_type: Data type (e.g., 'issue', 'search', 'transitions')
            format_name: Format identifier (e.g., 'human', 'ai')
            formatter: Formatter instance
        """
        key = (plugin, data_type, format_name)
        self._specific[key] = formatter

    def unregister_global(self, format_name: str) -> FormatterProtocol | None:
        """Unregister a global formatter."""
        return self._global.pop(format_name, None)

    def unregister(
        self,
        plugin: str,
        data_type: str,
        format_name: str,
    ) -> FormatterProtocol | None:
        """Unregister a plugin-specific formatter."""
        key = (plugin, data_type, format_name)
        return self._specific.pop(key, None)

    def get(
        self,
        format_name: str,
        plugin: str | None = None,
        data_type: str | None = None,
    ) -> FormatterProtocol | None:
        """Get formatter by lookup order.

        Lookup order:
        1. Plugin-specific: (plugin, data_type, format_name)
        2. Global: format_name

        Returns:
            Formatter or None if not found
        """
        # Try plugin-specific first
        if plugin and data_type:
            key = (plugin, data_type, format_name)
            if key in self._specific:
                return self._specific[key]

        # Fall back to global
        return self._global.get(format_name)

    def format(
        self,
        data: Any,
        format_name: str,
        plugin: str | None = None,
        data_type: str | None = None,
    ) -> str:
        """Format data using appropriate formatter.

        Args:
            data: Data to format
            format_name: Desired format (e.g., 'json', 'human', 'ai')
            plugin: Optional plugin name for specific formatting
            data_type: Optional data type for specific formatting

        Returns:
            Formatted string

        Raises:
            ValueError: If no formatter found for format_name
        """
        formatter = self.get(format_name, plugin, data_type)

        if formatter is None:
            raise ValueError(f"No formatter registered for format: {format_name}")

        return formatter.format(data)

    def available_formats(self) -> list[str]:
        """List available global format names."""
        return list(self._global.keys())

    def clear(self) -> None:
        """Clear all formatters."""
        self._global.clear()
        self._specific.clear()


# Global registry instance
formatter_registry = FormatterRegistry()


def format_response(
    data: Any,
    format_name: str,
    plugin: str | None = None,
    data_type: str | None = None,
) -> str:
    """Convenience function to format data using global registry.

    Args:
        data: Data to format
        format_name: Desired format
        plugin: Optional plugin name
        data_type: Optional data type

    Returns:
        Formatted string
    """
    return formatter_registry.format(data, format_name, plugin, data_type)
