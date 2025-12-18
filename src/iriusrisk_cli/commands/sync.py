"""
Sync command module for IriusRisk CLI.

This module provides functionality to synchronize and download threats and
countermeasures data from IriusRisk projects to local JSON files.
"""

import click
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from ..container import get_container
from ..api_client import IriusRiskApiClient
from ..utils.updates import get_update_tracker
from ..utils.project import resolve_project_id, get_project_context_info
from ..utils.project_resolution import resolve_project_id_to_uuid_strict as _resolve_project_id_to_uuid, is_uuid_format
from ..config import Config

logger = logging.getLogger(__name__)


def _ensure_iriusrisk_directory() -> Path:
    """Ensure the .iriusrisk directory exists in the current working directory.
    
    Returns:
        Path to the .iriusrisk directory
    """
    iriusrisk_dir = Path.cwd() / '.iriusrisk'
    iriusrisk_dir.mkdir(exist_ok=True)
    return iriusrisk_dir


def _download_threats_data(project_id: str, api_client: IriusRiskApiClient) -> Dict[str, Any]:
    """Download all threats data for a project.
    
    Args:
        project_id: Project ID to download threats for
        api_client: IriusRisk API client instance
        
    Returns:
        Dictionary containing threats data and metadata
    """
    click.echo("Downloading threats data...")
    
    # Get all threats (use large size to get all data)
    response = api_client.threat_client.get_threats(
        project_id=project_id,
        page=0,
        size=1000
    )
    
    # Handle different response formats
    if isinstance(response, __builtins__['list']):
        threats_data = response
        page_info = {}
    else:
        threats_data = response.get('_embedded', {}).get('items', [])
        page_info = response.get('page', {})
    
    # Create comprehensive data structure
    threats_sync_data = {
        'metadata': {
            'project_id': project_id,
            'data_type': 'threats',
            'total_count': len(threats_data),
            'page_info': page_info,
            'sync_timestamp': click.get_current_context().meta.get('sync_timestamp', 'unknown')
        },
        'threats': threats_data
    }
    
    click.echo(f"Downloaded {len(threats_data)} threat components")
    return threats_sync_data


def _download_countermeasures_data(project_id: str, api_client: IriusRiskApiClient) -> Dict[str, Any]:
    """Download all countermeasures data for a project.
    
    Args:
        project_id: Project ID to download countermeasures for
        api_client: IriusRisk API client instance
        
    Returns:
        Dictionary containing countermeasures data and metadata
    """
    click.echo("Downloading countermeasures data...")
    
    # Get all countermeasures (use large size to get all data)
    response = api_client.countermeasure_client.get_countermeasures(
        project_id=project_id,
        page=0,
        size=1000
    )
    
    # Handle different response formats
    if isinstance(response, __builtins__['list']):
        countermeasures_data = response
        page_info = {}
    else:
        countermeasures_data = response.get('_embedded', {}).get('items', [])
        page_info = response.get('page', {})
    
    # Create comprehensive data structure
    countermeasures_sync_data = {
        'metadata': {
            'project_id': project_id,
            'data_type': 'countermeasures',
            'total_count': len(countermeasures_data),
            'page_info': page_info,
            'sync_timestamp': click.get_current_context().meta.get('sync_timestamp', 'unknown')
        },
        'countermeasures': countermeasures_data
    }
    
    click.echo(f"Downloaded {len(countermeasures_data)} countermeasures")
    return countermeasures_sync_data


def _download_components_data(api_client: IriusRiskApiClient) -> Dict[str, Any]:
    """Download all system components data.
    
    Args:
        api_client: IriusRisk API client instance
    
    Returns:
        Dictionary containing components data and metadata
    """
    click.echo("Downloading system components data...")
    
    # Get all components (use large size to get all data)
    # Note: Components are system-wide, not project-specific
    response = api_client.project_client.get_components(
        page=0,
        size=1000  # This should get all components in one request
    )
    
    # Handle response format
    components_data = response.get('_embedded', {}).get('items', [])
    page_info = response.get('page', {})
    
    # If we have pagination, we need to get all pages
    total_pages = page_info.get('totalPages', 1)
    if total_pages > 1:
        click.echo(f"Found {total_pages} pages of components, downloading all...")
        
        all_components = components_data.copy()
        for page in range(1, total_pages):
            click.echo(f"Downloading page {page + 1} of {total_pages}...")
            page_response = api_client.project_client.get_components(page=page, size=1000)
            page_components = page_response.get('_embedded', {}).get('items', [])
            all_components.extend(page_components)
        
        components_data = all_components
        click.echo(f"Downloaded all {len(components_data)} components from {total_pages} pages")
    
    # Create comprehensive data structure
    components_sync_data = {
        'metadata': {
            'data_type': 'system_components',
            'total_count': len(components_data),
            'page_info': page_info,
            'sync_timestamp': click.get_current_context().meta.get('sync_timestamp', 'unknown')
        },
        'components': components_data
    }
    
    click.echo(f"Downloaded {len(components_data)} system components")
    return components_sync_data


def _download_trust_zones_data(api_client: IriusRiskApiClient) -> Dict[str, Any]:
    """Download all system trust zones data.
    
    Args:
        api_client: IriusRisk API client instance
    
    Returns:
        Dictionary containing trust zones data and metadata
    """
    click.echo("Downloading system trust zones data...")
    
    # Get all trust zones (use large size to get all data)
    # Note: Trust zones are system-wide, not project-specific
    response = api_client.project_client.get_trust_zones(
        page=0,
        size=1000  # This should get all trust zones in one request
    )
    
    # Handle response format
    trust_zones_data = response.get('_embedded', {}).get('items', [])
    page_info = response.get('page', {})
    
    # If we have pagination, we need to get all pages
    total_pages = page_info.get('totalPages', 1)
    if total_pages > 1:
        click.echo(f"Found {total_pages} pages of trust zones, downloading all...")
        
        all_trust_zones = trust_zones_data.copy()
        for page in range(1, total_pages):
            click.echo(f"Downloading page {page + 1} of {total_pages}...")
            page_response = api_client.project_client.get_trust_zones(page=page, size=1000)
            page_trust_zones = page_response.get('_embedded', {}).get('items', [])
            all_trust_zones.extend(page_trust_zones)
        
        trust_zones_data = all_trust_zones
        click.echo(f"Downloaded all {len(trust_zones_data)} trust zones from {total_pages} pages")
    
    # Create comprehensive data structure
    trust_zones_sync_data = {
        'metadata': {
            'data_type': 'system_trust_zones',
            'total_count': len(trust_zones_data),
            'page_info': page_info,
            'sync_timestamp': click.get_current_context().meta.get('sync_timestamp', 'unknown')
        },
        'trust_zones': trust_zones_data
    }
    
    click.echo(f"Downloaded {len(trust_zones_data)} system trust zones")
    return trust_zones_sync_data


def sync_data_to_directory(project_id: Optional[str] = None, 
                          output_dir: Optional[str] = None,
                          threats_only: bool = False,
                          countermeasures_only: bool = False, 
                          components_only: bool = False,
                          trust_zones_only: bool = False) -> Dict[str, Any]:
    """Core sync logic that can be used by both CLI and MCP.
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
        output_dir: Output directory (default: .iriusrisk in current directory)
        threats_only: Only sync threats data
        countermeasures_only: Only sync countermeasures data
        components_only: Only sync system components data
        
    Returns:
        Dictionary with sync results and metadata
    """
    from datetime import datetime
    
    # Set sync timestamp
    sync_timestamp = datetime.now().isoformat()
    results = {
        'timestamp': sync_timestamp,
        'components': None,
        'trust_zones': None,
        'threats': None,
        'countermeasures': None,
        'updates_applied': 0,
        'updates_failed': 0,
        'errors': [],
        'project_id': None,
        'project_name': None,
        'output_directory': None
    }
    
    try:
        # Get API client from container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        
        # Resolve project ID from argument or default configuration  
        resolved_project_id = None
        if project_id:
            resolved_project_id = project_id
        else:
            # Try to get default project ID from configuration
            config = Config()
            default_project_id = config.get_default_project_id()
            if default_project_id:
                resolved_project_id = default_project_id
        
        # Get project name for display
        project_name = get_project_context_info()
        results['project_name'] = project_name
        
        # Resolve project ID with fallback for API calls if we have one
        final_project_id = None
        if resolved_project_id:
            try:
                final_project_id = _resolve_project_id_to_uuid(resolved_project_id)
                results['project_id'] = final_project_id
                # Debug: verify we got a UUID
                if final_project_id == resolved_project_id and len(resolved_project_id) != 36:
                    # UUID resolution failed, this means the project might not exist or API lookup failed
                    click.echo(f"Warning: Could not resolve project reference '{resolved_project_id}' to UUID. Project may not exist or be inaccessible.")
                    final_project_id = None
            except Exception as e:
                click.echo(f"Warning: Failed to resolve project ID '{resolved_project_id}': {e}")
                final_project_id = None
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = _ensure_iriusrisk_directory()
        
        output_path.mkdir(exist_ok=True)
        results['output_directory'] = str(output_path.absolute())
        
        # Apply any pending updates before downloading fresh data
        if final_project_id:
            try:
                update_results = _apply_pending_updates(output_path, final_project_id, api_client)
                results['updates_applied'] = update_results.get('updates_applied', 0)
                results['updates_failed'] = update_results.get('updates_failed', 0)
                if update_results.get('errors'):
                    results['errors'].extend(update_results['errors'])
            except Exception as e:
                results['errors'].append(f"Update application failed: {e}")
        
        # Download and save components data (always, unless other specific flags)
        if not threats_only and not countermeasures_only and not trust_zones_only:
            try:
                components_data = _download_components_data(api_client)
                components_file = output_path / 'components.json'
                _save_json_file(components_data, components_file, 'components')
                results['components'] = {
                    'count': len(components_data.get('components', [])),
                    'file': str(components_file)
                }
            except Exception as e:
                results['errors'].append(f"Components sync failed: {e}")
        
        # Download and save trust zones data (always, unless other specific flags)
        if not threats_only and not countermeasures_only and not components_only:
            try:
                trust_zones_data = _download_trust_zones_data(api_client)
                trust_zones_file = output_path / 'trust-zones.json'
                _save_json_file(trust_zones_data, trust_zones_file, 'trust zones')
                results['trust_zones'] = {
                    'count': len(trust_zones_data.get('trust_zones', [])),
                    'file': str(trust_zones_file)
                }
            except Exception as e:
                results['errors'].append(f"Trust zones sync failed: {e}")
        
        # Download and save threats data (if project exists)
        if final_project_id and not countermeasures_only and not components_only and not trust_zones_only:
            try:
                threats_data = _download_threats_data(final_project_id, api_client)
                threats_file = output_path / 'threats.json'
                _save_json_file(threats_data, threats_file, 'threats')
                results['threats'] = {
                    'count': len(threats_data.get('threats', [])),
                    'file': str(threats_file)
                }
            except Exception as e:
                error_msg = f"Error downloading threats data: {e}"
                click.echo(error_msg, err=True)
                results['errors'].append(error_msg)
        
        # Download and save countermeasures data (if project exists)
        if final_project_id and not threats_only and not components_only and not trust_zones_only:
            try:
                countermeasures_data = _download_countermeasures_data(final_project_id, api_client)
                countermeasures_file = output_path / 'countermeasures.json'
                _save_json_file(countermeasures_data, countermeasures_file, 'countermeasures')
                results['countermeasures'] = {
                    'count': len(countermeasures_data.get('countermeasures', [])),
                    'file': str(countermeasures_file)
                }
            except Exception as e:
                error_msg = f"Error downloading countermeasures data: {e}"
                click.echo(error_msg, err=True)
                results['errors'].append(error_msg)
        
        # Inform user if no project was available for threats/countermeasures
        if not final_project_id and not components_only and not trust_zones_only:
            click.echo("No project configured - only downloaded system components and trust zones. Use 'iriusrisk init' to configure a project for threat and countermeasure data.")
                
    except Exception as e:
        # Ensure we don't get type errors when handling the exception
        error_message = f"Sync failed: {str(e)}" if e is not None else "Sync failed: Unknown error"
        results['errors'].append(error_message)
    
    return results


def _apply_pending_updates(output_path: Path, project_id: Optional[str] = None, api_client: Optional[IriusRiskApiClient] = None) -> Dict[str, Any]:
    """Apply any pending threat and countermeasure updates to IriusRisk.
    
    This function applies updates in batches with error handling and rollback capabilities.
    If critical errors occur, it can preserve the updates for retry.
    
    Args:
        output_path: Path to the .iriusrisk directory containing updates.json
        project_id: Resolved project UUID for API calls (required for issue creation)
        api_client: IriusRisk API client instance (optional, will create from container if not provided)
        
    Returns:
        Dictionary with update results and statistics
    """
    results = {
        "updates_applied": 0,
        "updates_failed": 0,
        "errors": [],
        "success_details": [],
        "comment_results": [],
        "rollback_available": False
    }
    
    tracker = None
    backup_updates = None
    
    try:
        tracker = get_update_tracker(output_path)
        pending_updates = tracker.get_pending_updates()
        
        if not pending_updates:
            click.echo("No pending updates to apply.")
            return results
        
        # Create backup of pending updates for potential rollback
        backup_updates = pending_updates.copy()
        
        click.echo(f"Applying {len(pending_updates)} pending updates to IriusRisk...")
        click.echo()
        
        # Get API client from container if not provided
        if api_client is None:
            container = get_container()
            api_client = container.get(IriusRiskApiClient)
        
        threat_client = api_client.threat_client
        countermeasure_client = api_client.countermeasure_client
        
        # Apply updates with individual error handling
        for i, update in enumerate(pending_updates):
            update_id = update["id"]
            update_type = update["type"]
            new_status = update.get("new_status", "")  # Not all update types have new_status
            reason = update.get("reason", "")
            context = update.get("context", "")
            comment = update.get("comment", "")
            
            try:
                # Show progress
                progress = f"({i+1}/{len(pending_updates)})"
                
                if update_type == "threat":
                    # Apply threat update
                    click.echo(f"  {progress} Updating threat {update_id[:8]}... -> {new_status}")
                    threat_client.update_threat_state(
                        threat_id=update_id,
                        state_transition=new_status,
                        reason=reason,
                        comment=comment
                    )
                    
                    # Create separate comment if provided
                    if comment:
                        # Validate comment length before attempting to create it
                        if len(comment) > 1000:
                            error_msg = f"Comment for threat {update_id[:8]} is too long ({len(comment)} chars, max: 1000). Skipping comment creation."
                            click.echo(f"    ⚠️  {error_msg}")
                            results["comment_results"].append(f"⚠️  {error_msg}")
                            results["errors"].append(error_msg)
                        else:
                            try:
                                results["comment_results"].append(f"Creating comment for threat {update_id[:8]}...")
                                threat_client.create_threat_comment(
                                    threat_id=update_id,
                                    comment=comment
                                )
                                results["comment_results"].append(f"✅ Comment created successfully for threat {update_id[:8]}")
                            except Exception as comment_error:
                                error_msg = f"Failed to create comment for threat {update_id[:8]}: {comment_error}"
                                results["comment_results"].append(f"❌ {error_msg}")
                                results["errors"].append(error_msg)
                                # Don't fail the entire update just because comment creation failed
                    
                elif update_type == "countermeasure":
                    # Apply countermeasure update  
                    click.echo(f"  {progress} Updating countermeasure {update_id[:8]}... -> {new_status}")
                    countermeasure_client.update_countermeasure_state(
                        countermeasure_id=update_id,
                        state_transition=new_status,
                        reason=reason,
                        comment=comment
                    )
                    
                    # Create separate comment if provided (countermeasure state API doesn't support comments)
                    if comment:
                        # Validate comment length before attempting to create it
                        if len(comment) > 1000:
                            error_msg = f"Comment for countermeasure {update_id[:8]} is too long ({len(comment)} chars, max: 1000). Skipping comment creation."
                            click.echo(f"    ⚠️  {error_msg}")
                            results["comment_results"].append(f"⚠️  {error_msg}")
                            results["errors"].append(error_msg)
                        else:
                            try:
                                results["comment_results"].append(f"Creating comment for countermeasure {update_id[:8]}...")
                                countermeasure_client.create_countermeasure_comment(
                                    countermeasure_id=update_id,
                                    comment=comment
                                )
                                results["comment_results"].append(f"✅ Comment created successfully for {update_id[:8]}")
                            except Exception as comment_error:
                                error_msg = f"Failed to create comment for {update_id[:8]}: {comment_error}"
                                results["comment_results"].append(f"❌ {error_msg}")
                                results["errors"].append(error_msg)
                                # Don't fail the entire update just because comment creation failed
                
                elif update_type == "issue_creation":
                    # Apply issue creation request
                    issue_tracker_id = update.get("issue_tracker_id")
                    click.echo(f"  {progress} Creating issue for countermeasure {update_id[:8]}...")
                    
                    # Use the project_id passed to this function
                    if not project_id:
                        raise Exception("No project ID provided for issue creation")
                    
                    countermeasure_client.create_countermeasure_issue(
                        project_id=project_id,
                        countermeasure_id=update_id,
                        issue_tracker_id=issue_tracker_id
                    )
                
                # Mark as applied immediately after successful API call
                if tracker.mark_update_applied(update_id, update_type):
                    results["updates_applied"] += 1
                    success_detail = {
                        "id": update_id,
                        "type": update_type
                    }
                    # Only add fields that exist for this update type
                    if new_status:
                        success_detail["status"] = new_status
                    if reason:
                        success_detail["reason"] = reason
                    if context:
                        success_detail["context"] = context
                    if comment:
                        success_detail["comment"] = comment
                    if update_type == "issue_creation":
                        success_detail["issue_tracker_id"] = update.get("issue_tracker_id")
                    
                    results["success_details"].append(success_detail)
                    click.echo(f"    ✅ Success")
                else:
                    # This shouldn't happen, but handle it gracefully
                    results["updates_failed"] += 1
                    results["errors"].append(f"Failed to mark {update_type} {update_id} as applied")
                
            except Exception as e:
                error_msg = f"Failed to update {update_type} {update_id[:8]}...: {str(e)}"
                click.echo(f"    ❌ {error_msg}")
                results["errors"].append(error_msg)
                results["updates_failed"] += 1
                
                # For authentication/connection errors, we might want to stop
                error_str = str(e).lower() if e is not None else ""
                if "authentication" in error_str or "connection" in error_str:
                    click.echo(f"  ⚠️  Connection/authentication error detected. Stopping update process.")
                    results["rollback_available"] = True
                    break
        
        # Summary
        if results["updates_applied"] > 0:
            click.echo(f"✅ Successfully applied {results['updates_applied']} updates to IriusRisk")
            
        if results["updates_failed"] > 0:
            click.echo(f"❌ Failed to apply {results['updates_failed']} updates")
            if results["rollback_available"]:
                click.echo("💡 Failed updates remain in queue for retry")
            
        # Clean up applied updates (but preserve failed ones)
        if results["updates_applied"] > 0:
            cleared_count = tracker.clear_applied_updates()
            if cleared_count > 0:
                click.echo(f"Cleared {cleared_count} successfully applied updates from queue")
        
        # Show retry information if there are failures
        if results["updates_failed"] > 0:
            remaining_count = len(tracker.get_pending_updates())
            if remaining_count > 0:
                click.echo(f"📝 {remaining_count} updates remain in queue for retry")
        
        click.echo()
        
    except Exception as e:
        error_msg = f"Critical error applying updates: {e}"
        click.echo(error_msg, err=True)
        results["errors"].append(error_msg)
        results["rollback_available"] = True
        
        # If we have a backup and tracker, ensure failed updates are preserved
        if backup_updates and tracker:
            try:
                # Check what's still pending vs what we backed up
                current_pending = tracker.get_pending_updates()
                if len(current_pending) < len(backup_updates):
                    click.echo("⚠️  Some updates may have been lost. Updates preserved for retry.")
            except Exception as preserve_error:
                click.echo(f"⚠️  Could not verify update preservation: {preserve_error}")
    
    return results


def _save_json_file(data: Dict[str, Any], file_path: Path, data_type: str) -> None:
    """Save data to a JSON file with proper formatting.
    
    Args:
        data: Data to save
        file_path: Path to save the file
        data_type: Type of data being saved (for logging)
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        file_size = file_path.stat().st_size
        click.echo(f"Saved {data_type} data to {file_path} ({file_size:,} bytes)")
    except Exception as e:
        click.echo(f"Error saving {data_type} data to {file_path}: {e}", err=True)
        raise


@click.command()
@click.argument('project_id', required=False)
@click.option('--threats-only', is_flag=True, help='Only sync threats data')
@click.option('--countermeasures-only', is_flag=True, help='Only sync countermeasures data')
@click.option('--components-only', is_flag=True, help='Only sync system components data')
@click.option('--trust-zones-only', is_flag=True, help='Only sync system trust zones data')
@click.option('--output-dir', '-o', help='Output directory (default: .iriusrisk)')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['json', 'pretty'], case_sensitive=False),
              default='pretty', help='Output format for JSON files')
def sync(project_id: Optional[str], threats_only: bool, countermeasures_only: bool, 
         components_only: bool, trust_zones_only: bool, output_dir: Optional[str], output_format: str):
    """Synchronize threats, countermeasures, system components, and trust zones data to local JSON files.
    
    This command downloads all threats and countermeasures data for a project,
    plus all system components and trust zones data, and saves them as JSON files in the 
    .iriusrisk directory for offline analysis.
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
    """
    from datetime import datetime
    
    logger.info("Starting sync operation")
    logger.debug(f"Sync parameters: project_id={project_id}, threats_only={threats_only}, "
                f"countermeasures_only={countermeasures_only}, components_only={components_only}, "
                f"trust_zones_only={trust_zones_only}, output_dir={output_dir}, format={output_format}")
    
    # Set sync timestamp
    sync_timestamp = datetime.now().isoformat()
    click.get_current_context().meta['sync_timestamp'] = sync_timestamp
    logger.debug(f"Sync timestamp: {sync_timestamp}")
    
    try:
        # Get API client from container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        
        # Resolve project ID from argument or default configuration
        resolved_project_id = resolve_project_id(project_id)
        logger.debug(f"Resolved project ID: {resolved_project_id}")
        
        # Show context information if using default project
        if not project_id:
            project_name = get_project_context_info()
            if project_name:
                logger.info(f"Using default project: {project_name}")
                click.echo(f"Using default project: {project_name}")
            click.echo()
        
        # Resolve project ID with fallback for API calls
        final_project_id = None
        project_resolution_failed = False
        
        if resolved_project_id:
            try:
                logger.debug(f"Attempting to resolve project ID '{resolved_project_id}' to UUID")
                final_project_id = _resolve_project_id_to_uuid(resolved_project_id)
                # Check if resolution actually worked
                if final_project_id == resolved_project_id and len(resolved_project_id) != 36:
                    # UUID resolution failed, project might not exist
                    logger.warning(f"Could not resolve project reference '{resolved_project_id}' to UUID")
                    click.echo(f"Warning: Could not resolve project reference '{resolved_project_id}' to UUID. Project may not exist or be inaccessible.")
                    click.echo("Will download system components only.")
                    final_project_id = None
                    project_resolution_failed = True
                else:
                    logger.info(f"Successfully resolved project ID to UUID: {final_project_id}")
            except Exception as e:
                logger.warning(f"Failed to resolve project ID '{resolved_project_id}': {e}")
                click.echo(f"Warning: Failed to resolve project ID '{resolved_project_id}': {e}")
                click.echo("Will download system components only.")
                final_project_id = None
                project_resolution_failed = True
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Using custom output directory: {output_path}")
        else:
            output_path = _ensure_iriusrisk_directory()
            logger.debug(f"Using default .iriusrisk directory: {output_path}")
        
        logger.info(f"Synchronizing data to: {output_path.absolute()}")
        click.echo(f"Synchronizing data to: {output_path.absolute()}")
        click.echo(f"Sync timestamp: {sync_timestamp}")
        click.echo()
        
        # Apply any pending updates before downloading fresh data
        if final_project_id:
            logger.info("Applying pending updates before downloading fresh data")
            _apply_pending_updates(output_path, final_project_id, api_client)
        
        # Download and save threats data (only if we have a valid project)
        if not countermeasures_only and not components_only and not trust_zones_only:
            if final_project_id:
                try:
                    logger.info("Downloading threats data")
                    threats_data = _download_threats_data(final_project_id, api_client)
                    threats_file = output_path / 'threats.json'
                    _save_json_file(threats_data, threats_file, 'threats')
                    logger.info(f"Successfully downloaded {len(threats_data.get('threats', []))} threats")
                except Exception as e:
                    logger.error(f"Error downloading threats data: {e}")
                    click.echo(f"Error downloading threats data: {e}", err=True)
                    if threats_only:  # Only fail if we're doing threats-only and it fails
                        raise click.Abort()
            elif threats_only:
                # User specifically requested threats-only but no project available
                logger.error("Cannot download threats data without a valid project")
                click.echo("Error: Cannot download threats data without a valid project. Use 'iriusrisk init' to configure a project.", err=True)
                raise click.Abort()
        
        # Download and save countermeasures data (only if we have a valid project)
        if not threats_only and not components_only and not trust_zones_only:
            if final_project_id:
                try:
                    logger.info("Downloading countermeasures data")
                    countermeasures_data = _download_countermeasures_data(final_project_id, api_client)
                    countermeasures_file = output_path / 'countermeasures.json'
                    _save_json_file(countermeasures_data, countermeasures_file, 'countermeasures')
                    logger.info(f"Successfully downloaded {len(countermeasures_data.get('countermeasures', []))} countermeasures")
                except Exception as e:
                    logger.error(f"Error downloading countermeasures data: {e}")
                    click.echo(f"Error downloading countermeasures data: {e}", err=True)
                    if countermeasures_only:  # Only fail if we're doing countermeasures-only and it fails
                        raise click.Abort()
            elif countermeasures_only:
                # User specifically requested countermeasures-only but no project available
                logger.error("Cannot download countermeasures data without a valid project")
                click.echo("Error: Cannot download countermeasures data without a valid project. Use 'iriusrisk init' to configure a project.", err=True)
                raise click.Abort()
        
        # Download and save components data
        if not threats_only and not countermeasures_only and not trust_zones_only:
            try:
                logger.info("Downloading system components data")
                components_data = _download_components_data(api_client)
                components_file = output_path / 'components.json'
                _save_json_file(components_data, components_file, 'components')
                logger.info(f"Successfully downloaded {len(components_data.get('components', []))} components")
            except Exception as e:
                logger.error(f"Error downloading components data: {e}")
                click.echo(f"Error downloading components data: {e}", err=True)
                if not components_only:  # Only fail if we're not doing components-only
                    raise click.Abort()
        
        # Download and save trust zones data
        if not threats_only and not countermeasures_only and not components_only:
            try:
                logger.info("Downloading system trust zones data")
                trust_zones_data = _download_trust_zones_data(api_client)
                trust_zones_file = output_path / 'trust-zones.json'
                _save_json_file(trust_zones_data, trust_zones_file, 'trust zones')
                logger.info(f"Successfully downloaded {len(trust_zones_data.get('trust_zones', []))} trust zones")
            except Exception as e:
                logger.error(f"Error downloading trust zones data: {e}")
                click.echo(f"Error downloading trust zones data: {e}", err=True)
                if trust_zones_only:  # Only fail if we're doing trust-zones-only and it fails
                    raise click.Abort()
        
        # Download trust zones only if specifically requested
        if trust_zones_only:
            try:
                logger.info("Downloading system trust zones data (trust-zones-only mode)")
                trust_zones_data = _download_trust_zones_data(api_client)
                trust_zones_file = output_path / 'trust-zones.json'
                _save_json_file(trust_zones_data, trust_zones_file, 'trust zones')
                logger.info(f"Successfully downloaded {len(trust_zones_data.get('trust_zones', []))} trust zones")
            except Exception as e:
                logger.error(f"Error downloading trust zones data: {e}")
                click.echo(f"Error downloading trust zones data: {e}", err=True)
                raise click.Abort()
        
        click.echo()
        logger.info("Synchronization completed successfully")
        click.echo("✅ Synchronization completed successfully!")
        
        # Show summary
        files_created = []
        if not countermeasures_only and not components_only and not trust_zones_only:
            threats_file = output_path / 'threats.json'
            if threats_file.exists():
                files_created.append(f"threats ({threats_file})")
                click.echo(f"📄 Threats data: {threats_file}")
        
        if not threats_only and not components_only and not trust_zones_only:
            countermeasures_file = output_path / 'countermeasures.json'
            if countermeasures_file.exists():
                files_created.append(f"countermeasures ({countermeasures_file})")
                click.echo(f"📄 Countermeasures data: {countermeasures_file}")
        
        if not threats_only and not countermeasures_only and not trust_zones_only:
            components_file = output_path / 'components.json'
            if components_file.exists():
                files_created.append(f"components ({components_file})")
                click.echo(f"📄 Components data: {components_file}")
        
        if not threats_only and not countermeasures_only and not components_only:
            trust_zones_file = output_path / 'trust-zones.json'
            if trust_zones_file.exists():
                files_created.append(f"trust zones ({trust_zones_file})")
                click.echo(f"📄 Trust zones data: {trust_zones_file}")
        
        if trust_zones_only:
            trust_zones_file = output_path / 'trust-zones.json'
            if trust_zones_file.exists():
                files_created.append(f"trust zones ({trust_zones_file})")
                click.echo(f"📄 Trust zones data: {trust_zones_file}")
        
        logger.info(f"Created {len(files_created)} data files: {', '.join([f.split(' (')[0] for f in files_created])}")
        
        # Show helpful message if project resolution failed
        if project_resolution_failed and not components_only:
            click.echo()
            click.echo("💡 To sync threats and countermeasures, configure a project with 'iriusrisk init' or check that your project exists and is accessible.")                                                        
        
    except Exception as e:
        logger.error(f"Error during synchronization: {e}")
        click.echo(f"Error during synchronization: {e}", err=True)
        raise click.Abort()


def sync_data_to_directory(project_id: Optional[str] = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Synchronize IriusRisk data to a specified directory.
    
    This is the shared sync logic used by both CLI and MCP interfaces.
    It applies pending updates first, then downloads fresh data.
    
    Args:
        project_id: Project ID to sync (optional)
        output_dir: Output directory path (defaults to .iriusrisk in current directory)
        
    Returns:
        Dictionary containing sync results and metadata
    """
    from datetime import datetime
    
    # Set up output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = _ensure_iriusrisk_directory()
    
    output_path.mkdir(exist_ok=True)
    
    # Initialize results
    results = {
        'timestamp': datetime.now().isoformat(),
        'output_directory': str(output_path),
        'project_id': project_id,
        'components': None,
        'trust_zones': None,
        'threats': None,
        'countermeasures': None,
        'updates_applied': 0,
        'updates_failed': 0,
        'failed_updates': [],
        'debug_messages': [f"sync_data_to_directory called with project_id='{project_id}', output_dir='{output_dir}'"]
    }
    
    try:
        # Get API client from container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        
        # Download components data (always available, no project needed)
        try:
            components_data = _download_components_data(api_client)
            components_file = output_path / 'components.json'
            _save_json_file(components_data, components_file, 'components')
            results['components'] = {
                'count': len(components_data.get('components', [])),
                'file': str(components_file)
            }
            results['debug_messages'].append(f"Downloaded {len(components_data.get('components', []))} components")
        except Exception as e:
            results['errors'] = results.get('errors', [])
            results['errors'].append(f"Failed to download components: {e}")
        
        # Download trust zones data (always available, no project needed)
        try:
            trust_zones_data = _download_trust_zones_data(api_client)
            trust_zones_file = output_path / 'trust-zones.json'
            _save_json_file(trust_zones_data, trust_zones_file, 'trust zones')
            results['trust_zones'] = {
                'count': len(trust_zones_data.get('trust_zones', [])),
                'file': str(trust_zones_file)
            }
            results['debug_messages'].append(f"Downloaded {len(trust_zones_data.get('trust_zones', []))} trust zones")
        except Exception as e:
            results['errors'] = results.get('errors', [])
            results['errors'].append(f"Failed to download trust zones: {e}")
        
        # Resolve project ID if provided (for project-specific operations)
        final_project_id = None
        if project_id:
            try:
                final_project_id = _resolve_project_id_to_uuid(project_id)
                results['project_id'] = final_project_id
                # Validate that we got a proper UUID
                if not is_uuid_format(final_project_id):
                    raise Exception(f"Could not resolve reference ID '{project_id}' to a valid UUID. Got: '{final_project_id}'")
                
                # Apply any pending updates (now that we have a valid project ID)
                results['debug_messages'].append("About to call _apply_pending_updates()")
                update_results = _apply_pending_updates(output_path, final_project_id, api_client)
                results['debug_messages'].append(f"_apply_pending_updates returned: {update_results}")
                results.update(update_results)
                
            except Exception as e:
                # Project resolution failed, but that's OK - we still have components/trust zones
                results['project_resolution_error'] = str(e)
                results['debug_messages'].append(f"Project resolution failed: {e}")
                final_project_id = None
        
        # Download project-specific data if project ID is available
        if final_project_id:
            try:
                # Download threats
                threats_data = _download_threats_data(final_project_id, api_client)
                threats_file = output_path / 'threats.json'
                _save_json_file(threats_data, threats_file, 'threats')
                
                results['threats'] = {
                    'count': threats_data.get('metadata', {}).get('total_count', 0),
                    'file': str(threats_file)
                }
            except Exception as e:
                results['threats'] = {'error': str(e)}
            
            try:
                # Download countermeasures
                countermeasures_data = _download_countermeasures_data(final_project_id, api_client)
                countermeasures_file = output_path / 'countermeasures.json'
                _save_json_file(countermeasures_data, countermeasures_file, 'countermeasures')
                
                results['countermeasures'] = {
                    'count': countermeasures_data.get('metadata', {}).get('total_count', 0),
                    'file': str(countermeasures_file)
                }
            except Exception as e:
                results['countermeasures'] = {'error': str(e)}
        
        return results
        
    except Exception as e:
        results['error'] = str(e)
        return results
