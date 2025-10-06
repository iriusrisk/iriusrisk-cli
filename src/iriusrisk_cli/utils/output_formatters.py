"""Output formatting utilities for IriusRisk CLI.

This module provides centralized output formatting functionality to ensure
consistent formatting across all CLI commands.
"""

import json
import csv
import sys
from typing import List, Dict, Any, Optional, Union, Callable
from io import StringIO
import click

from .table import TableFormatter


class OutputFormatter:
    """Centralized output formatting for consistent display across commands."""
    
    # Supported output formats
    SUPPORTED_FORMATS = ['table', 'json', 'csv']
    
    @staticmethod
    def format_output(data: Any, 
                     output_format: str, 
                     headers: Optional[List[str]] = None,
                     title: Optional[str] = None,
                     table_format: Optional[str] = None,
                     csv_headers: Optional[List[str]] = None,
                     row_transformer: Optional[Callable[[Any], List[Any]]] = None,
                     dict_transformer: Optional[Callable[[Any], Dict[str, Any]]] = None) -> str:
        """Format data according to the specified output format.
        
        Args:
            data: Data to format (list, dict, or any JSON-serializable object)
            output_format: Output format ('table', 'json', 'csv')
            headers: Column headers for table format
            title: Optional title for table format
            table_format: Tabulate format for table output
            csv_headers: Headers for CSV output (if different from table headers)
            row_transformer: Function to transform each item to a table row
            dict_transformer: Function to transform each item to a CSV dict
            
        Returns:
            Formatted string ready for output
            
        Raises:
            ValueError: If output_format is not supported
        """
        if output_format not in OutputFormatter.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}. "
                           f"Supported formats: {', '.join(OutputFormatter.SUPPORTED_FORMATS)}")
        
        if output_format == 'json':
            return OutputFormatter._format_json(data)
        elif output_format == 'csv':
            return OutputFormatter._format_csv(data, csv_headers, dict_transformer)
        else:  # table format
            return OutputFormatter._format_table(data, headers, title, table_format, row_transformer)
    
    @staticmethod
    def print_output(data: Any, 
                    output_format: str, 
                    headers: Optional[List[str]] = None,
                    title: Optional[str] = None,
                    table_format: Optional[str] = None,
                    csv_headers: Optional[List[str]] = None,
                    row_transformer: Optional[Callable[[Any], List[Any]]] = None,
                    dict_transformer: Optional[Callable[[Any], Dict[str, Any]]] = None):
        """Print formatted data to stdout.
        
        Args:
            data: Data to format and print
            output_format: Output format ('table', 'json', 'csv')
            headers: Column headers for table format
            title: Optional title for table format
            table_format: Tabulate format for table output
            csv_headers: Headers for CSV output (if different from table headers)
            row_transformer: Function to transform each item to a table row
            dict_transformer: Function to transform each item to a CSV dict
        """
        formatted_output = OutputFormatter.format_output(
            data, output_format, headers, title, table_format, 
            csv_headers, row_transformer, dict_transformer
        )
        click.echo(formatted_output)
    
    @staticmethod
    def _format_json(data: Any) -> str:
        """Format data as JSON with consistent indentation."""
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def _format_csv(data: Any, 
                   headers: Optional[List[str]] = None,
                   dict_transformer: Optional[Callable[[Any], Dict[str, Any]]] = None) -> str:
        """Format data as CSV.
        
        Args:
            data: Data to format (should be a list of items)
            headers: CSV headers
            dict_transformer: Function to transform each item to a dict for CSV output
            
        Returns:
            CSV formatted string
        """
        if not data:
            return ""
        
        # Handle case where data is not a list
        if not isinstance(data, list):
            data = [data]
        
        output = StringIO()
        
        if dict_transformer and headers:
            # Use DictWriter for structured output
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            
            for item in data:
                row_dict = dict_transformer(item)
                writer.writerow(row_dict)
        else:
            # Use regular writer for simple output
            writer = csv.writer(output)
            
            if headers:
                writer.writerow(headers)
            
            # If data items are already lists/tuples, write them directly
            # Otherwise, try to convert to list
            for item in data:
                if isinstance(item, (list, tuple)):
                    writer.writerow(item)
                elif isinstance(item, dict):
                    # If headers provided, extract values in header order
                    if headers:
                        row = [item.get(header, '') for header in headers]
                    else:
                        row = list(item.values())
                    writer.writerow(row)
                else:
                    # Single value
                    writer.writerow([item])
        
        return output.getvalue()
    
    @staticmethod
    def _format_table(data: Any, 
                     headers: Optional[List[str]] = None,
                     title: Optional[str] = None,
                     table_format: Optional[str] = None,
                     row_transformer: Optional[Callable[[Any], List[Any]]] = None) -> str:
        """Format data as a table.
        
        Args:
            data: Data to format
            headers: Table headers
            title: Optional table title
            table_format: Tabulate format
            row_transformer: Function to transform each item to a table row
            
        Returns:
            Table formatted string
        """
        if not data:
            return "No data to display."
        
        # Handle case where data is not a list
        if not isinstance(data, list):
            data = [data]
        
        # Transform data to table rows
        if row_transformer:
            rows = [row_transformer(item) for item in data]
        else:
            # Default transformation
            rows = []
            for item in data:
                if isinstance(item, (list, tuple)):
                    rows.append(list(item))
                elif isinstance(item, dict):
                    if headers:
                        row = [item.get(header, '') for header in headers]
                    else:
                        row = list(item.values())
                    rows.append(row)
                else:
                    rows.append([item])
        
        # Format table
        result = ""
        if title:
            result += f"{title}\n"
            result += "=" * len(title) + "\n"
        
        if headers:
            result += TableFormatter.format_table(rows, headers, table_format)
        else:
            # No headers - just format the data
            result += TableFormatter.format_table(rows, [], table_format)
        
        return result


class ListOutputFormatter:
    """Specialized formatter for list-based commands (projects, threats, etc.)."""
    
    @staticmethod
    def format_list_output(items: List[Dict[str, Any]], 
                          output_format: str,
                          table_config: Dict[str, Any],
                          csv_config: Dict[str, Any],
                          page_info: Optional[Dict[str, Any]] = None,
                          full_response: Optional[Dict[str, Any]] = None) -> str:
        """Format list output with pagination info.
        
        Args:
            items: List of items to format
            output_format: Output format ('table', 'json', 'csv')
            table_config: Configuration for table formatting
            csv_config: Configuration for CSV formatting
            page_info: Pagination information
            full_response: Full API response (for JSON output)
            
        Returns:
            Formatted output string
        """
        if output_format == 'json':
            # For JSON, return the full response if available, otherwise just the items
            data = full_response if full_response else items
            return OutputFormatter._format_json(data)
        
        elif output_format == 'csv':
            return OutputFormatter._format_csv(
                items,
                headers=csv_config.get('headers'),
                dict_transformer=csv_config.get('dict_transformer')
            )
        
        else:  # table format
            table_output = OutputFormatter._format_table(
                items,
                headers=table_config.get('headers'),
                title=table_config.get('title'),
                table_format=table_config.get('table_format'),
                row_transformer=table_config.get('row_transformer')
            )
            
            # Add pagination info for table format
            if page_info:
                pagination_info = ListOutputFormatter._format_pagination_info(items, page_info)
                table_output += "\n" + pagination_info
            
            return table_output
    
    @staticmethod
    def print_list_output(items: List[Dict[str, Any]], 
                         output_format: str,
                         table_config: Dict[str, Any],
                         csv_config: Dict[str, Any],
                         page_info: Optional[Dict[str, Any]] = None,
                         full_response: Optional[Dict[str, Any]] = None):
        """Print formatted list output to stdout."""
        if not items:
            click.echo("No items found matching the criteria.")
            return
        
        formatted_output = ListOutputFormatter.format_list_output(
            items, output_format, table_config, csv_config, page_info, full_response
        )
        click.echo(formatted_output)
    
    @staticmethod
    def _format_pagination_info(items: List[Any], page_info: Dict[str, Any]) -> str:
        """Format pagination information."""
        total_elements = page_info.get('totalElements', 0)
        current_page = page_info.get('number', 0)
        total_pages = page_info.get('totalPages', 0)
        size = page_info.get('size', 0)
        
        return (f"Showing page {current_page + 1} of {total_pages} "
                f"({len(items)} of {total_elements} items, {size} per page)")


class DetailOutputFormatter:
    """Specialized formatter for detail/show commands."""
    
    @staticmethod
    def format_detail_output(item: Dict[str, Any], 
                           output_format: str,
                           detail_formatter: Optional[Callable[[Dict[str, Any]], None]] = None) -> str:
        """Format detail output for a single item.
        
        Args:
            item: Item to format
            output_format: Output format ('table', 'json')
            detail_formatter: Custom formatter function for table output
            
        Returns:
            Formatted output string
        """
        if output_format == 'json':
            return OutputFormatter._format_json(item)
        else:
            # For table format, we need to use the custom formatter
            # Since it prints directly, we'll capture its output
            if detail_formatter:
                # This is a bit tricky since most detail formatters print directly
                # For now, we'll return a placeholder and let the caller handle it
                return "TABLE_FORMAT_HANDLED_BY_CUSTOM_FORMATTER"
            else:
                # Default key-value table format
                return TableFormatter.format_key_value_table(item)
    
    @staticmethod
    def print_detail_output(item: Dict[str, Any], 
                          output_format: str,
                          detail_formatter: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Print formatted detail output to stdout."""
        if output_format == 'json':
            click.echo(OutputFormatter._format_json(item))
        else:
            # For table format, use the custom formatter if provided
            if detail_formatter:
                detail_formatter(item)
            else:
                # Default key-value table format
                TableFormatter.print_key_value_table(item, "Item Details")


# Convenience functions for common patterns
def format_and_print_list(items: List[Dict[str, Any]], 
                         output_format: str,
                         table_headers: List[str],
                         csv_headers: List[str],
                         row_transformer: Callable[[Dict[str, Any]], List[Any]],
                         csv_transformer: Callable[[Dict[str, Any]], Dict[str, Any]],
                         title: Optional[str] = None,
                         page_info: Optional[Dict[str, Any]] = None,
                         full_response: Optional[Dict[str, Any]] = None):
    """Convenience function for common list formatting pattern."""
    table_config = {
        'headers': table_headers,
        'title': title,
        'row_transformer': row_transformer
    }
    
    csv_config = {
        'headers': csv_headers,
        'dict_transformer': csv_transformer
    }
    
    ListOutputFormatter.print_list_output(
        items, output_format, table_config, csv_config, page_info, full_response
    )


def format_and_print_detail(item: Dict[str, Any], 
                           output_format: str,
                           detail_formatter: Optional[Callable[[Dict[str, Any]], None]] = None):
    """Convenience function for common detail formatting pattern."""
    DetailOutputFormatter.print_detail_output(item, output_format, detail_formatter)



