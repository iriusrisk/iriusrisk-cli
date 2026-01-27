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


def _wait_for_threat_model_sync(project_id: str, api_client: IriusRiskApiClient, verbose: bool = True, timeout: int = 300) -> None:
    """Wait for threat model synchronization to complete.
    
    Polls the project state until it reaches 'synced' or times out.
    
    Args:
        project_id: Project UUID
        api_client: IriusRisk API client instance
        verbose: If True, output progress messages
        timeout: Maximum time to wait in seconds (default: 5 minutes)
        
    Raises:
        Exception: If timeout is reached or state check fails repeatedly
    """
    import time
    
    if verbose:
        click.echo("⏳ Waiting for threat model synchronization to complete...")
    
    start_time = time.time()
    poll_interval = 2  # Start with 2 second intervals
    max_poll_interval = 10  # Max 10 seconds between polls
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    while True:
        elapsed = time.time() - start_time
        
        # Check timeout
        if elapsed > timeout:
            error_msg = f"Timeout waiting for threat model sync after {timeout} seconds"
            if verbose:
                click.echo(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        try:
            # Get current project state
            project_data = api_client.project_client.get_project(project_id)
            state = project_data.get('state', 'unknown')
            operation = project_data.get('operation', 'none')
            
            # Reset error counter on successful check
            consecutive_errors = 0
            
            if state == 'synced':
                if verbose:
                    click.echo(f"✅ Threat model synchronized (took {elapsed:.1f} seconds)")
                return
            elif state in ['syncing', 'syncing-draft']:
                if verbose:
                    click.echo(f"   Still synchronizing... (elapsed: {elapsed:.0f}s, state: {state})")
            elif state == 'draft':
                # Still in draft after triggering - might need more time for rules to start
                if verbose:
                    click.echo(f"   Waiting for rules engine to start... (elapsed: {elapsed:.0f}s)")
            else:
                if verbose:
                    click.echo(f"   Unexpected state: {state} (operation: {operation}, elapsed: {elapsed:.0f}s)")
            
            # Wait before next poll (exponential backoff)
            time.sleep(min(poll_interval, max_poll_interval))
            poll_interval = min(poll_interval * 1.5, max_poll_interval)
            
        except Exception as e:
            consecutive_errors += 1
            if verbose:
                click.echo(f"   Warning: Failed to check state ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                error_msg = f"Failed to check project state {max_consecutive_errors} times in a row"
                if verbose:
                    click.echo(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # Wait a bit before retrying
            time.sleep(poll_interval)


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


def _download_questionnaires_data(project_id: str, api_client: IriusRiskApiClient) -> Dict[str, Any]:
    """Download all questionnaires data for a project.
    
    Args:
        project_id: Project ID to download questionnaires for
        api_client: IriusRisk API client instance
        
    Returns:
        Dictionary containing questionnaires data and metadata
    """
    click.echo("Downloading questionnaires data...")
    
    # Get project questionnaire
    try:
        project_questionnaire = api_client.questionnaire_client.get_project_questionnaire(project_id=project_id)
        click.echo("  Downloaded project questionnaire")
    except Exception as e:
        error_msg = f"Could not download project questionnaire: {e}"
        logger.error(error_msg)
        click.echo(f"  Warning: {error_msg}")
        project_questionnaire = None
    
    # Get all component questionnaires summary
    try:
        component_summaries_response = api_client.questionnaire_client.get_all_component_questionnaires(
            project_id=project_id,
            page=0,
            size=1000
        )
        component_summaries = component_summaries_response.get('_embedded', {}).get('items', [])
        if component_summaries:
            click.echo(f"  Found {len(component_summaries)} components with questionnaires")
    except Exception as e:
        error_msg = f"Could not download component questionnaires list: {e}"
        logger.error(error_msg)
        click.echo(f"  Warning: {error_msg}")
        component_summaries = []
    
    # Get detailed questionnaires for each component
    detailed_components = []
    for i, summary_item in enumerate(component_summaries):
        component_data = summary_item.get('component', {})
        component_id = component_data.get('id')
        component_name = component_data.get('name', 'Unknown')
        component_ref_id = component_data.get('ref', '')
        questionnaire_status = summary_item.get('status', 'UNKNOWN')
        
        if not component_id:
            continue
        
        click.echo(f"  ({i+1}/{len(component_summaries)}) Downloading questionnaire for {component_name}...")
        
        try:
            questionnaire_data = api_client.questionnaire_client.get_component_questionnaire(component_id=component_id)
            
            detailed_entry = {
                'componentId': component_id,
                'componentName': component_name,
                'componentReferenceId': component_ref_id,
                'status': questionnaire_status,
                'questionnaire': questionnaire_data.get('questionnaire', {}),
                'conclusions': questionnaire_data.get('conclusions', []),
                'outcomes': questionnaire_data.get('outcomes', {})
            }
            
            detailed_components.append(detailed_entry)
        except Exception as e:
            error_msg = f"Failed to download questionnaire for {component_name}: {e}"
            logger.warning(error_msg)
            click.echo(f"    Warning: {error_msg}")
            continue
    
    # Create comprehensive data structure
    questionnaires_sync_data = {
        'metadata': {
            'project_id': project_id,
            'data_type': 'questionnaires',
            'sync_timestamp': click.get_current_context().meta.get('sync_timestamp', 'unknown'),
            'component_count': len(detailed_components)
        },
        'project': {
            'projectId': project_id,
            'questionnaire': project_questionnaire.get('questionnaire', {}) if project_questionnaire else {},
            'conclusions': project_questionnaire.get('conclusions', []) if project_questionnaire else [],
            'outcomes': project_questionnaire.get('outcomes', {}) if project_questionnaire else {}
        } if project_questionnaire else None,
        'components': detailed_components
    }
    
    click.echo(f"Downloaded project questionnaire and {len(detailed_components)} component questionnaires")
    return questionnaires_sync_data


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


def sync_data_to_directory(
    project_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    threats_only: bool = False,
    countermeasures_only: bool = False,
    components_only: bool = False,
    trust_zones_only: bool = False,
    check_config_for_default: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """Core sync logic that can be used by both CLI and MCP.
    
    This is the unified synchronization function that downloads data from IriusRisk
    and saves it locally. It supports selective syncing via flags and can be configured
    for different calling contexts (CLI vs MCP).
    
    Args:
        project_id: Project UUID or reference ID (optional if default project configured)
        output_dir: Output directory (default: .iriusrisk in current directory)
        threats_only: Only sync threats data
        countermeasures_only: Only sync countermeasures data
        components_only: Only sync system components data
        trust_zones_only: Only sync system trust zones data
        check_config_for_default: If True, check Config for default project when project_id is None
        verbose: If True, output progress messages via click.echo()
        
    Returns:
        Dictionary with sync results and metadata:
        {
            'timestamp': str,
            'output_directory': str,
            'project_id': Optional[str],
            'project_name': Optional[str],
            'components': Optional[Dict],
            'trust_zones': Optional[Dict],
            'threats': Optional[Dict],
            'countermeasures': Optional[Dict],
            'updates_applied': int,
            'updates_failed': int,
            'errors': List[str],
            'comment_results': List[str]
        }
    """
    from datetime import datetime
    
    # Initialize results with consistent structure
    sync_timestamp = datetime.now().isoformat()
    results = {
        'timestamp': sync_timestamp,
        'output_directory': None,
        'project_id': None,
        'project_name': None,
        'components': None,
        'trust_zones': None,
        'threats': None,
        'countermeasures': None,
        'questionnaires': None,
        'updates_applied': 0,
        'updates_failed': 0,
        'errors': [],
        'comment_results': []
    }
    
    try:
        # Get API client from container
        container = get_container()
        api_client = container.get(IriusRiskApiClient)
        
        # Resolve project ID from argument or default configuration
        resolved_project_id = None
        if project_id:
            resolved_project_id = project_id
        elif check_config_for_default:
            # Try to get default project ID from configuration (CLI mode)
            try:
                config = Config()
                default_project_id = config.get_default_project_id()
                if default_project_id:
                    resolved_project_id = default_project_id
            except Exception as e:
                if verbose:
                    click.echo(f"Warning: Could not read config: {e}")
        
        # Get project name for display
        if resolved_project_id:
            try:
                project_name = get_project_context_info()
                results['project_name'] = project_name
            except Exception:
                pass  # Not critical if we can't get project name
        
        # Resolve project ID to UUID for API calls
        final_project_id = None
        if resolved_project_id:
            try:
                final_project_id = _resolve_project_id_to_uuid(resolved_project_id, api_client.project_client)
                results['project_id'] = final_project_id
                
                # Validate that we got a proper UUID
                if not is_uuid_format(final_project_id):
                    warning_msg = f"Could not resolve project reference '{resolved_project_id}' to UUID"
                    if verbose:
                        click.echo(f"Warning: {warning_msg}")
                    results['errors'].append(warning_msg)
                    final_project_id = None
                    
            except Exception as e:
                warning_msg = f"Failed to resolve project ID '{resolved_project_id}': {e}"
                if verbose:
                    click.echo(f"Warning: {warning_msg}")
                results['errors'].append(warning_msg)
                final_project_id = None
        
        # Check project state at start and trigger rules if needed
        if final_project_id:
            try:
                if verbose:
                    click.echo("Checking project threat model state...")
                project_data = api_client.project_client.get_project(final_project_id)
                state = project_data.get('state', 'unknown')
                
                if state == 'draft':
                    if verbose:
                        click.echo("⚠️  Project has pending changes (state: draft)")
                        click.echo("🔄 Triggering threat model update...")
                    
                    try:
                        api_client.project_client.execute_rules(final_project_id)
                        if verbose:
                            click.echo("✅ Threat model update triggered successfully")
                        
                        # Wait for rules execution to complete
                        _wait_for_threat_model_sync(final_project_id, api_client, verbose)
                        
                    except Exception as rules_error:
                        error_msg = f"Failed to trigger threat model update: {rules_error}"
                        if verbose:
                            click.echo(f"⚠️  {error_msg}")
                        results['errors'].append(error_msg)
                elif state == 'synced':
                    if verbose:
                        click.echo("✅ Project threat model is up to date (state: synced)")
                elif state in ['syncing', 'syncing-draft']:
                    if verbose:
                        click.echo(f"⏳ Project threat model is currently updating (state: {state})")
                    # Wait for ongoing sync to complete
                    _wait_for_threat_model_sync(final_project_id, api_client, verbose)
                else:
                    if verbose:
                        click.echo(f"ℹ️  Project state: {state}")
                        
                if verbose:
                    click.echo()
            except Exception as state_check_error:
                # Don't fail the entire sync if state check fails
                if verbose:
                    click.echo(f"Warning: Could not check project state: {state_check_error}")
                click.echo()
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = _ensure_iriusrisk_directory()
        
        output_path.mkdir(parents=True, exist_ok=True)
        results['output_directory'] = str(output_path.absolute())
        
        # Apply any pending updates before downloading fresh data
        if final_project_id:
            try:
                update_results = _apply_pending_updates(output_path, final_project_id, api_client)
                results['updates_applied'] = update_results.get('updates_applied', 0)
                results['updates_failed'] = update_results.get('updates_failed', 0)
                if update_results.get('errors'):
                    results['errors'].extend(update_results['errors'])
                if update_results.get('comment_results'):
                    results['comment_results'] = update_results['comment_results']
            except Exception as e:
                error_msg = f"Update application failed: {e}"
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(error_msg, err=True)
        
        # Download and save components data (unless specific other-only flags)
        if not threats_only and not countermeasures_only and not trust_zones_only:
            try:
                if verbose:
                    click.echo("Downloading system components data...")
                components_data = _download_components_data(api_client)
                components_file = output_path / 'components.json'
                _save_json_file(components_data, components_file, 'components' if verbose else None)
                results['components'] = {
                    'count': len(components_data.get('components', [])),
                    'file': str(components_file)
                }
            except Exception as e:
                error_msg = f"Components sync failed: {e}"
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(error_msg, err=True)
        
        # Download and save trust zones data (unless specific other-only flags)
        if not threats_only and not countermeasures_only and not components_only:
            try:
                if verbose:
                    click.echo("Downloading system trust zones data...")
                trust_zones_data = _download_trust_zones_data(api_client)
                trust_zones_file = output_path / 'trust-zones.json'
                _save_json_file(trust_zones_data, trust_zones_file, 'trust zones' if verbose else None)
                results['trust_zones'] = {
                    'count': len(trust_zones_data.get('trust_zones', [])),
                    'file': str(trust_zones_file)
                }
            except Exception as e:
                error_msg = f"Trust zones sync failed: {e}"
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(error_msg, err=True)
        
        # Download and save threats data (if project exists and not excluded)
        if final_project_id and not countermeasures_only and not components_only and not trust_zones_only:
            try:
                if verbose:
                    click.echo("Downloading threats data...")
                threats_data = _download_threats_data(final_project_id, api_client)
                threats_file = output_path / 'threats.json'
                _save_json_file(threats_data, threats_file, 'threats' if verbose else None)
                results['threats'] = {
                    'count': len(threats_data.get('threats', [])),
                    'file': str(threats_file)
                }
            except Exception as e:
                error_msg = f"Error downloading threats data: {e}"
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(error_msg, err=True)
        
        # Download and save countermeasures data (if project exists and not excluded)
        if final_project_id and not threats_only and not components_only and not trust_zones_only:
            try:
                if verbose:
                    click.echo("Downloading countermeasures data...")
                countermeasures_data = _download_countermeasures_data(final_project_id, api_client)
                countermeasures_file = output_path / 'countermeasures.json'
                _save_json_file(countermeasures_data, countermeasures_file, 'countermeasures' if verbose else None)
                results['countermeasures'] = {
                    'count': len(countermeasures_data.get('countermeasures', [])),
                    'file': str(countermeasures_file)
                }
            except Exception as e:
                error_msg = f"Error downloading countermeasures data: {e}"
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(error_msg, err=True)
        
        # Download and save questionnaires data (if project exists and not excluded)
        if final_project_id and not threats_only and not components_only and not trust_zones_only and not countermeasures_only:
            try:
                if verbose:
                    click.echo("Downloading questionnaires data...")
                questionnaires_data = _download_questionnaires_data(final_project_id, api_client)
                questionnaires_file = output_path / 'questionnaires.json'
                _save_json_file(questionnaires_data, questionnaires_file, 'questionnaires' if verbose else None)
                
                project_count = 1 if questionnaires_data.get('project') else 0
                component_count = len(questionnaires_data.get('components', []))
                results['questionnaires'] = {
                    'project_count': project_count,
                    'component_count': component_count,
                    'file': str(questionnaires_file)
                }
            except Exception as e:
                error_msg = f"Error downloading questionnaires data: {e}"
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(error_msg, err=True)
        
        # Download and save current threat model as OTM (if project exists and not excluded)
        # This supports multi-repository workflows where subsequent repos need to merge with existing model
        should_download_otm = (
            final_project_id and 
            not threats_only and 
            not components_only and 
            not trust_zones_only and 
            not countermeasures_only
        )
        
        logger.info(f"OTM download check: final_project_id={final_project_id}, should_download={should_download_otm}")
        logger.debug(f"Flags: threats_only={threats_only}, countermeasures_only={countermeasures_only}, "
                    f"components_only={components_only}, trust_zones_only={trust_zones_only}")
        
        if should_download_otm:
            try:
                logger.info(f"Starting OTM download for project: {final_project_id}")
                if verbose:
                    click.echo("Downloading current threat model (OTM)...")
                
                # Get project data to obtain reference ID (V1 OTM export endpoint may need it)
                project_data = api_client.project_client.get_project(final_project_id)
                reference_id = project_data.get('referenceId') or project_data.get('ref') or final_project_id
                logger.info(f"Using reference ID for OTM export: {reference_id}")
                
                # Export the current threat model from IriusRisk using reference ID
                logger.debug(f"Calling api_client.project_client.export_project_as_otm({reference_id})")
                otm_content = api_client.project_client.export_project_as_otm(reference_id)
                logger.info(f"Successfully retrieved OTM content: {len(otm_content)} bytes")
                
                otm_file = output_path / 'current-threat-model.otm'
                logger.debug(f"Saving OTM to: {otm_file}")
                
                # Save OTM content to file
                with open(otm_file, 'w', encoding='utf-8') as f:
                    f.write(otm_content)
                
                logger.info(f"Saved OTM to file: {otm_file}")
                if verbose:
                    click.echo(f"✓ Saved current threat model to {otm_file}")
                
                results['threat_model_otm'] = {
                    'size': len(otm_content),
                    'file': str(otm_file)
                }
                logger.info("OTM download completed successfully")
            except Exception as e:
                # OTM export failure - log detailed error and report it
                error_msg = f"Failed to export threat model as OTM: {e}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                if verbose:
                    click.echo(f"⚠️  {error_msg}", err=True)
                # Store failure info so MCP can report it
                results['threat_model_otm'] = {
                    'error': str(e)
                }
        else:
            logger.info("OTM download skipped: conditions not met")
        
        # Inform user if no project was available for threats/countermeasures/questionnaires
        if not final_project_id and not components_only and not trust_zones_only and verbose:
            click.echo("No project configured - only downloaded system components and trust zones. Use 'iriusrisk init' to configure a project for threat, countermeasure, and questionnaire data.")
        
        # Check project state at end and trigger rules if needed
        if final_project_id:
            try:
                if verbose:
                    click.echo()
                    click.echo("Checking project threat model state after sync...")
                project_data = api_client.project_client.get_project(final_project_id)
                state = project_data.get('state', 'unknown')
                
                if state == 'draft':
                    if verbose:
                        click.echo("⚠️  Project has pending changes (state: draft)")
                        click.echo("🔄 Triggering threat model update...")
                    
                    try:
                        api_client.project_client.execute_rules(final_project_id)
                        if verbose:
                            click.echo("✅ Threat model update triggered successfully")
                        
                        # Wait for rules execution to complete
                        _wait_for_threat_model_sync(final_project_id, api_client, verbose)
                        
                    except Exception as rules_error:
                        error_msg = f"Failed to trigger threat model update: {rules_error}"
                        if verbose:
                            click.echo(f"⚠️  {error_msg}")
                        results['errors'].append(error_msg)
                elif state == 'synced':
                    if verbose:
                        click.echo("✅ Project threat model is up to date (state: synced)")
                elif state in ['syncing', 'syncing-draft']:
                    if verbose:
                        click.echo(f"⏳ Project threat model is currently updating (state: {state})")
                    # Wait for ongoing sync to complete
                    _wait_for_threat_model_sync(final_project_id, api_client, verbose)
                else:
                    if verbose:
                        click.echo(f"ℹ️  Project state: {state}")
            except Exception as state_check_error:
                # Don't fail the entire sync if state check fails
                if verbose:
                    click.echo(f"Warning: Could not check project state after sync: {state_check_error}")
                
    except Exception as e:
        # Ensure we don't get type errors when handling the exception
        error_message = f"Sync failed: {str(e)}" if e is not None else "Sync failed: Unknown error"
        results['errors'].append(error_message)
        if verbose:
            click.echo(error_message, err=True)
    
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
        questionnaire_client = api_client.questionnaire_client
        
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
                
                elif update_type == "project_questionnaire":
                    # Apply project questionnaire update
                    answers_data = update.get("answers_data", {})
                    click.echo(f"  {progress} Updating project questionnaire for project {update_id[:8]}...")
                    
                    # Use the project_id passed to this function (should match update_id)
                    questionnaire_client.update_project_questionnaire(
                        project_id=update_id,
                        questionnaire_data=answers_data
                    )
                    click.echo(f"    ✅ Project questionnaire updated, rules engine will regenerate threats")
                
                elif update_type == "component_questionnaire":
                    # Apply component questionnaire update
                    answers_data = update.get("answers_data", {})
                    click.echo(f"  {progress} Updating component questionnaire for component {update_id[:8]}...")
                    
                    questionnaire_client.update_component_questionnaire(
                        component_id=update_id,
                        questionnaire_data=answers_data
                    )
                    click.echo(f"    ✅ Component questionnaire updated, rules engine will regenerate threats")
                
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
                    if update_type in ["project_questionnaire", "component_questionnaire"]:
                        success_detail["answers_data"] = update.get("answers_data")
                    
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


def _save_json_file(data: Dict[str, Any], file_path: Path, data_type: Optional[str] = None) -> None:
    """Save data to a JSON file with proper formatting.
    
    Args:
        data: Data to save
        file_path: Path to save the file
        data_type: Type of data being saved (for logging). If None, no output is produced.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if data_type:  # Only output if data_type provided (verbose mode)
            file_size = file_path.stat().st_size
            click.echo(f"Saved {data_type} data to {file_path} ({file_size:,} bytes)")
    except Exception as e:
        if data_type:  # Only output error if verbose
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
              default='pretty', help='Output format for JSON files (currently unused)')
def sync(project_id: Optional[str], threats_only: bool, countermeasures_only: bool, 
         components_only: bool, trust_zones_only: bool, output_dir: Optional[str], output_format: str):
    """Synchronize threats, countermeasures, questionnaires, system components, and trust zones data to local JSON files.
    
    This command downloads all threats, countermeasures, and questionnaires data for a project,
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
    
    sync_timestamp = datetime.now().isoformat()
    logger.debug(f"Sync timestamp: {sync_timestamp}")
    
    try:
        # Show context information if using default project
        if not project_id:
            try:
                project_name = get_project_context_info()
                if project_name:
                    logger.info(f"Using default project: {project_name}")
                    click.echo(f"Using default project: {project_name}")
            except Exception:
                pass  # Not critical if we can't get project context
            click.echo()
        
        # Display sync header
        output_path = Path(output_dir) if output_dir else Path.cwd() / '.iriusrisk'
        logger.info(f"Synchronizing data to: {output_path.absolute()}")
        click.echo(f"Synchronizing data to: {output_path.absolute()}")
        click.echo(f"Sync timestamp: {sync_timestamp}")
        click.echo()
        
        # Call the shared sync function
        results = sync_data_to_directory(
            project_id=project_id,
            output_dir=output_dir,
            threats_only=threats_only,
            countermeasures_only=countermeasures_only,
            components_only=components_only,
            trust_zones_only=trust_zones_only,
            check_config_for_default=True,
            verbose=True
        )
        
        # Check for critical errors that should abort
        has_critical_error = False
        
        # Check if specific-only sync failed
        if threats_only and (not results.get('threats') or results.get('threats', {}).get('error')):
            logger.error("Cannot download threats data - see errors")
            click.echo("Error: Cannot download threats data. Use 'iriusrisk init' to configure a project.", err=True)
            has_critical_error = True
            
        if countermeasures_only and (not results.get('countermeasures') or results.get('countermeasures', {}).get('error')):
            logger.error("Cannot download countermeasures data - see errors")
            click.echo("Error: Cannot download countermeasures data. Use 'iriusrisk init' to configure a project.", err=True)
            has_critical_error = True
        
        if components_only and (not results.get('components') or results.get('components', {}).get('error')):
            logger.error("Cannot download components data - see errors")
            has_critical_error = True
            
        if trust_zones_only and (not results.get('trust_zones') or results.get('trust_zones', {}).get('error')):
            logger.error("Cannot download trust zones data - see errors")
            has_critical_error = True
        
        if has_critical_error:
            raise click.Abort()
        
        # Display success message
        click.echo()
        logger.info("Synchronization completed successfully")
        click.echo("✅ Synchronization completed successfully!")
        
        # Show summary of files created
        output_path_resolved = Path(results['output_directory'])
        if results.get('threats') and not results['threats'].get('error'):
            threats_file = output_path_resolved / 'threats.json'
            if threats_file.exists():
                click.echo(f"📄 Threats data: {threats_file}")
                logger.info(f"Created threats file: {threats_file}")
        
        if results.get('countermeasures') and not results['countermeasures'].get('error'):
            countermeasures_file = output_path_resolved / 'countermeasures.json'
            if countermeasures_file.exists():
                click.echo(f"📄 Countermeasures data: {countermeasures_file}")
                logger.info(f"Created countermeasures file: {countermeasures_file}")
        
        if results.get('components') and not results['components'].get('error'):
            components_file = output_path_resolved / 'components.json'
            if components_file.exists():
                click.echo(f"📄 Components data: {components_file}")
                logger.info(f"Created components file: {components_file}")
        
        if results.get('trust_zones') and not results['trust_zones'].get('error'):
            trust_zones_file = output_path_resolved / 'trust-zones.json'
            if trust_zones_file.exists():
                click.echo(f"📄 Trust zones data: {trust_zones_file}")
                logger.info(f"Created trust zones file: {trust_zones_file}")
        
        if results.get('questionnaires') and not results['questionnaires'].get('error'):
            questionnaires_file = output_path_resolved / 'questionnaires.json'
            if questionnaires_file.exists():
                click.echo(f"📄 Questionnaires data: {questionnaires_file}")
                logger.info(f"Created questionnaires file: {questionnaires_file}")
        
        if results.get('threat_model_otm'):
            otm_file = output_path_resolved / 'current-threat-model.otm'
            if otm_file.exists():
                click.echo(f"📄 Current threat model (OTM): {otm_file}")
                logger.info(f"Created threat model OTM file: {otm_file}")
                click.echo(f"   💡 Use this file as basis for threat model updates in multi-repository workflows")
        
        # Show helpful message if project couldn't be resolved
        if not results.get('project_id') and not components_only and not trust_zones_only:
            click.echo()
            click.echo("💡 To sync threats, countermeasures, and questionnaires, configure a project with 'iriusrisk init' or check that your project exists and is accessible.")
        
    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Error during synchronization: {e}")
        click.echo(f"Error during synchronization: {e}", err=True)
        raise click.Abort()
