"""Table formatting utilities for IriusRisk CLI."""

import click
import textwrap
from typing import List, Dict, Any, Optional, Callable
from tabulate import tabulate


class TableFormatter:
    """Centralized table formatting for consistent output across commands."""
    
    DEFAULT_TABLE_FORMAT = 'grid'
    MAX_TABLE_WIDTH = 100  # Maximum table width in characters
    MAX_CELL_WIDTH = 80    # Maximum width for individual cells
    
    @staticmethod
    def wrap_cell_text(text: str, max_width: int = None) -> str:
        """Wrap text in a table cell to fit within max width.
        
        Args:
            text: Text to wrap
            max_width: Maximum width for the cell (defaults to MAX_CELL_WIDTH)
            
        Returns:
            Wrapped text with newlines
        """
        if not text or not isinstance(text, str):
            return str(text) if text is not None else ""
        
        max_width = max_width or TableFormatter.MAX_CELL_WIDTH
        
        # If text is already short enough, return as-is
        if len(text) <= max_width:
            return text
        
        # Wrap the text
        return textwrap.fill(text, width=max_width, break_long_words=False, break_on_hyphens=False)
    
    @staticmethod
    def wrap_table_data(data: List[List[Any]], max_width: int = None) -> List[List[Any]]:
        """Wrap all text in table data.
        
        Args:
            data: List of rows, where each row is a list of values
            max_width: Maximum width for cells
            
        Returns:
            Data with wrapped text
        """
        max_width = max_width or TableFormatter.MAX_CELL_WIDTH
        wrapped_data = []
        for row in data:
            wrapped_row = [TableFormatter.wrap_cell_text(str(cell), max_width) for cell in row]
            wrapped_data.append(wrapped_row)
        return wrapped_data
    
    @staticmethod
    def format_table(data: List[List[Any]], 
                    headers: List[str], 
                    table_format: str = None) -> str:
        """Format data as a table.
        
        Args:
            data: List of rows, where each row is a list of values
            headers: List of column headers
            table_format: Tabulate format (defaults to grid)
            
        Returns:
            Formatted table string
        """
        fmt = table_format or TableFormatter.DEFAULT_TABLE_FORMAT
        # Wrap text in cells before passing to tabulate
        wrapped_data = TableFormatter.wrap_table_data(data)
        return tabulate(wrapped_data, headers=headers, tablefmt=fmt)
    
    @staticmethod
    def print_table(data: List[List[Any]], 
                   headers: List[str], 
                   title: Optional[str] = None,
                   table_format: str = None):
        """Print a formatted table to stdout.
        
        Args:
            data: List of rows, where each row is a list of values
            headers: List of column headers
            title: Optional title to display above the table
            table_format: Tabulate format (defaults to grid)
        """
        if title:
            click.echo(title)
            click.echo("=" * len(title))
        
        table = TableFormatter.format_table(data, headers, table_format)
        click.echo(table)
    
    @staticmethod
    def format_key_value_table(data: Dict[str, Any], 
                              field_header: str = "Field",
                              value_header: str = "Value",
                              table_format: str = None) -> str:
        """Format a dictionary as a key-value table.
        
        Args:
            data: Dictionary to format
            field_header: Header for the key column
            value_header: Header for the value column
            table_format: Tabulate format (defaults to grid)
            
        Returns:
            Formatted table string
        """
        rows = [[key, value] for key, value in data.items()]
        return TableFormatter.format_table(rows, [field_header, value_header], table_format)
    
    @staticmethod
    def print_key_value_table(data: Dict[str, Any], 
                             title: Optional[str] = None,
                             field_header: str = "Field",
                             value_header: str = "Value",
                             table_format: str = None):
        """Print a dictionary as a key-value table.
        
        Args:
            data: Dictionary to format
            title: Optional title to display above the table
            field_header: Header for the key column
            value_header: Header for the value column
            table_format: Tabulate format (defaults to grid)
        """
        if title:
            click.echo(title)
            click.echo("=" * len(title))
        
        table = TableFormatter.format_key_value_table(data, field_header, value_header, table_format)
        click.echo(table)
    
    @staticmethod
    def print_section_separator(title: str, char: str = "-"):
        """Print a section separator.
        
        Args:
            title: Section title
            char: Character to use for separator line
        """
        click.echo(f"\n{title}:")
        click.echo(char * len(f"{title}:"))
    
    @staticmethod
    def truncate_field(value: str, max_length: int = 50, suffix: str = "...") -> str:
        """Truncate a field value if it's too long.
        
        Args:
            value: Value to truncate
            max_length: Maximum length before truncation
            suffix: Suffix to add when truncating
            
        Returns:
            Truncated value
        """
        if not value or len(value) <= max_length:
            return value
        return value[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_boolean(value: Any) -> str:
        """Format a boolean value consistently.
        
        Args:
            value: Boolean or truthy value
            
        Returns:
            "Yes" or "No"
        """
        return "Yes" if value else "No"
    
    @staticmethod
    def format_optional(value: Any, default: str = "N/A") -> str:
        """Format an optional value with a default.
        
        Args:
            value: Value to format
            default: Default value if None or empty
            
        Returns:
            Formatted value or default
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        return str(value)
    
    @staticmethod
    def format_list(items: List[Any], separator: str = ", ", max_items: int = None) -> str:
        """Format a list of items as a string.
        
        Args:
            items: List of items to format
            separator: Separator between items
            max_items: Maximum number of items to show (adds "..." if exceeded)
            
        Returns:
            Formatted string
        """
        if not items:
            return ""
        
        str_items = [str(item) for item in items]
        
        if max_items and len(str_items) > max_items:
            displayed_items = str_items[:max_items]
            return separator.join(displayed_items) + f"{separator}... ({len(str_items) - max_items} more)"
        
        return separator.join(str_items)
    
    @staticmethod
    def format_nested_value(data: Dict[str, Any], key_path: str, default: str = "N/A") -> str:
        """Extract and format a nested value from a dictionary.
        
        Args:
            data: Dictionary to extract from
            key_path: Dot-separated path to the value (e.g., "workflowState.name")
            default: Default value if key not found
            
        Returns:
            Formatted value or default
        """
        keys = key_path.split('.')
        current = data
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return TableFormatter.format_optional(current, default)
        except (KeyError, TypeError, AttributeError):
            return default
    
    @staticmethod
    def format_timestamp(timestamp: str, format_type: str = "date") -> str:
        """Format a timestamp string.
        
        Args:
            timestamp: ISO timestamp string
            format_type: "date", "datetime", or "time"
            
        Returns:
            Formatted timestamp
        """
        if not timestamp:
            return "N/A"
        
        try:
            from datetime import datetime
            # Try to parse ISO format
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                # Assume it's already a date string
                return timestamp
            
            if format_type == "date":
                return dt.strftime("%Y-%m-%d")
            elif format_type == "time":
                return dt.strftime("%H:%M:%S")
            else:  # datetime
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, ImportError):
            # If parsing fails, return truncated original
            return TableFormatter.truncate_field(timestamp, 19)
    
    @staticmethod
    def create_row_transformer(field_mappings: List[Dict[str, Any]]) -> Callable[[Dict[str, Any]], List[Any]]:
        """Create a row transformer function from field mappings.
        
        Args:
            field_mappings: List of field mapping dictionaries with keys:
                - 'key': Key path in the data (supports dot notation)
                - 'formatter': Optional formatter function
                - 'default': Default value if key not found
                - 'truncate': Max length for truncation
                
        Returns:
            Function that transforms a data dict to a table row
        """
        def transformer(data: Dict[str, Any]) -> List[Any]:
            row = []
            for mapping in field_mappings:
                key_path = mapping['key']
                formatter = mapping.get('formatter')
                default = mapping.get('default', 'N/A')
                truncate = mapping.get('truncate')
                
                # Extract value
                if '.' in key_path:
                    value = TableFormatter.format_nested_value(data, key_path, default)
                else:
                    value = TableFormatter.format_optional(data.get(key_path), default)
                
                # Apply custom formatter
                if formatter:
                    value = formatter(value)
                
                # Apply truncation
                if truncate and isinstance(value, str):
                    value = TableFormatter.truncate_field(value, truncate)
                
                row.append(value)
            
            return row
        
        return transformer
    
    @staticmethod
    def create_csv_transformer(field_mappings: List[Dict[str, Any]]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """Create a CSV transformer function from field mappings.
        
        Args:
            field_mappings: List of field mapping dictionaries with keys:
                - 'key': Key path in the data (supports dot notation)
                - 'csv_key': Key to use in CSV output (defaults to 'key')
                - 'formatter': Optional formatter function
                - 'default': Default value if key not found
                
        Returns:
            Function that transforms a data dict to a CSV dict
        """
        def transformer(data: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for mapping in field_mappings:
                key_path = mapping['key']
                csv_key = mapping.get('csv_key', key_path.split('.')[-1])  # Use last part of path as default
                formatter = mapping.get('formatter')
                default = mapping.get('default', '')
                
                # Extract value
                if '.' in key_path:
                    value = TableFormatter.format_nested_value(data, key_path, default)
                else:
                    value = data.get(key_path, default)
                
                # Apply custom formatter
                if formatter:
                    value = formatter(value)
                
                result[csv_key] = value
            
            return result
        
        return transformer


# Convenience functions for common use cases
def print_projects_table(projects: List[Dict], include_versions: bool = False, page_info: Dict = None):
    """Print a table of projects with consistent formatting."""
    headers = ['ID', 'Name', 'Reference ID', 'Workflow State', 'Archived', 'Updated']
    
    if include_versions:
        headers.append('Version')
    
    rows = []
    for project in projects:
        workflow_state = project.get('workflowState', {})
        workflow_name = TableFormatter.format_optional(
            workflow_state.get('name') if workflow_state else None
        )
        
        row = [
            TableFormatter.truncate_field(str(project.get('id', 'N/A')), 12),  # Truncate UUID
            TableFormatter.format_optional(project.get('name')),
            TableFormatter.format_optional(project.get('referenceId')),
            workflow_name,
            TableFormatter.format_boolean(project.get('isArchived', False)),
            TableFormatter.truncate_field(
                TableFormatter.format_optional(project.get('modelUpdated')), 10
            )  # Show date only
        ]
        
        if include_versions:
            version = project.get('version', {})
            version_name = TableFormatter.format_optional(
                version.get('name') if version else None
            )
            row.append(version_name)
        
        rows.append(row)
    
    TableFormatter.print_table(rows, headers)
    
    # Show pagination info
    if page_info:
        total_elements = page_info.get('totalElements', 0)
        current_page = page_info.get('number', 0)
        total_pages = page_info.get('totalPages', 0)
        size = page_info.get('size', 0)
        
        click.echo(f"\nShowing page {current_page + 1} of {total_pages} "
                  f"({len(projects)} of {total_elements} projects, {size} per page)")


def print_project_details(project: Dict):
    """Print detailed project information with consistent formatting."""
    # Basic project information
    basic_info = {
        'ID': TableFormatter.format_optional(project.get('id')),
        'Name': TableFormatter.format_optional(project.get('name')),
        'Reference ID': TableFormatter.format_optional(project.get('referenceId')),
        'Description': TableFormatter.format_optional(project.get('description'), 'No description'),
        'Tags': TableFormatter.format_optional(project.get('tags'), 'No tags'),
        'State': TableFormatter.format_optional(project.get('state')),
        'Model Updated': TableFormatter.format_optional(project.get('modelUpdated')),
    }
    
    # Workflow state information
    workflow_state = project.get('workflowState', {})
    if workflow_state:
        basic_info.update({
            'Workflow State': TableFormatter.format_optional(workflow_state.get('name')),
            'Workflow State ID': TableFormatter.format_optional(workflow_state.get('uuid')),
            'Workflow Reference': TableFormatter.format_optional(workflow_state.get('referenceId')),
            'Locks Threat Model': TableFormatter.format_boolean(workflow_state.get('isLockThreatModel', False)),
        })
    
    # Status flags
    basic_info.update({
        'Archived': TableFormatter.format_boolean(project.get('isArchived', False)),
        'Blueprint': TableFormatter.format_boolean(project.get('isBlueprint', False)),
        'Threat Model Locked': TableFormatter.format_boolean(project.get('isThreatModelLocked', False)),
        'Read Only': TableFormatter.format_boolean(project.get('readOnly', False)),
    })
    
    # Version information
    version = project.get('version')
    if version:
        basic_info.update({
            'Version Name': TableFormatter.format_optional(version.get('name')),
            'Version ID': TableFormatter.format_optional(version.get('id')),
        })
    
    # Operation information
    operation = project.get('operation')
    if operation:
        basic_info['Operation'] = str(operation)
    
    TableFormatter.print_key_value_table(basic_info, "Project Information")
    
    # Custom fields
    custom_fields = project.get('customFields')
    if custom_fields and custom_fields.get('customFieldValues'):
        TableFormatter.print_section_separator("Custom Fields")
        cf_data = []
        for cf in custom_fields['customFieldValues']:
            cf_data.append([
                TableFormatter.format_optional(cf.get('customField', {}).get('name')),
                TableFormatter.format_optional(cf.get('value'))
            ])
        TableFormatter.print_table(cf_data, ['Field', 'Value'])
    
    # Links (if available)
    links = project.get('_links', {})
    if links:
        TableFormatter.print_section_separator("Available Links")
        link_data = []
        for link_name, link_info in links.items():
            if isinstance(link_info, dict) and 'href' in link_info:
                link_data.append([link_name, link_info['href']])
        if link_data:
            TableFormatter.print_table(link_data, ['Relation', 'URL'])
