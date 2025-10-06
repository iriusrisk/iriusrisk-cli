"""
Updates command module for IriusRisk CLI.

This module provides functionality to manage tracked threat and countermeasure
status updates that are queued for synchronization with IriusRisk.
"""

import click
import json
from pathlib import Path
from typing import Optional
from ..utils.updates import get_update_tracker
from ..utils.project import get_project_context_info


@click.group()
def updates():
    """Manage tracked threat and countermeasure status updates.
    
    This command group provides functionality to view, manage, and manually
    apply status updates that have been tracked for synchronization with IriusRisk.
    """
    pass


@updates.command()
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
def list(output_format: str):
    """List all pending status updates.
    
    Shows all threat and countermeasure status updates that are queued
    for synchronization with IriusRisk.
    """
    try:
        # Find .iriusRisk directory
        iriusrisk_dir = Path.cwd() / '.iriusRisk'
        if not iriusrisk_dir.exists():
            click.echo("No .iriusRisk directory found. Run 'iriusrisk sync' first.", err=True)
            raise click.Abort()
        
        tracker = get_update_tracker(iriusrisk_dir)
        pending_updates = tracker.get_pending_updates()
        stats = tracker.get_stats()
        
        if output_format == 'json':
            output_data = {
                'pending_updates': pending_updates,
                'stats': stats
            }
            click.echo(json.dumps(output_data, indent=2))
            return
        
        # Table format
        if not pending_updates:
            click.echo("No pending updates.")
            return
        
        click.echo(f"Pending Status Updates ({len(pending_updates)} total)")
        click.echo("=" * 60)
        click.echo()
        
        for i, update in enumerate(pending_updates, 1):
            click.echo(f"{i}. {update['type'].title()}: {update['id']}")
            click.echo(f"   Status: {update['new_status']}")
            click.echo(f"   Reason: {update['reason']}")
            if update.get('context'):
                click.echo(f"   Context: {update['context']}")
            click.echo(f"   Tracked: {update['timestamp']}")
            click.echo()
        
        click.echo(f"📊 Statistics:")
        click.echo(f"   Total pending: {stats['pending_updates']}")
        click.echo(f"   Threats: {len([u for u in pending_updates if u['type'] == 'threat'])}")
        click.echo(f"   Countermeasures: {len([u for u in pending_updates if u['type'] == 'countermeasure'])}")
        click.echo()
        click.echo("💡 Use 'iriusrisk sync' to apply these updates to IriusRisk")
        
    except Exception as e:
        click.echo(f"Error listing updates: {e}", err=True)
        raise click.Abort()


@updates.command()
@click.option('--applied', is_flag=True, help='Also show applied updates')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json'], case_sensitive=False),
              default='table', help='Output format')
def stats(applied: bool, output_format: str):
    """Show statistics about tracked updates."""
    try:
        # Find .iriusRisk directory
        iriusrisk_dir = Path.cwd() / '.iriusRisk'
        if not iriusrisk_dir.exists():
            click.echo("No .iriusRisk directory found. Run 'iriusrisk sync' first.", err=True)
            raise click.Abort()
        
        tracker = get_update_tracker(iriusrisk_dir)
        stats = tracker.get_stats()
        
        if output_format == 'json':
            if applied:
                all_updates = tracker.get_all_updates()
                stats['all_updates'] = all_updates
            click.echo(json.dumps(stats, indent=2))
            return
        
        # Table format
        click.echo("Update Statistics")
        click.echo("=" * 30)
        click.echo(f"Total updates: {stats['total_updates']}")
        click.echo(f"Pending: {stats['pending_updates']}")
        click.echo(f"Applied: {stats['applied_updates']}")
        click.echo()
        click.echo(f"By type:")
        click.echo(f"  Threats: {stats['threat_updates']}")
        click.echo(f"  Countermeasures: {stats['countermeasure_updates']}")
        click.echo()
        click.echo(f"Last sync: {stats['last_sync'] or 'Never'}")
        click.echo(f"Updates file: {stats['updates_file']}")
        
        if applied and stats['applied_updates'] > 0:
            click.echo()
            click.echo("Recent Applied Updates:")
            all_updates = tracker.get_all_updates()
            applied_updates = [u for u in all_updates if u.get('applied', False)]
            
            for update in applied_updates[-5:]:  # Show last 5 applied
                applied_time = update.get('applied_timestamp', 'Unknown')
                click.echo(f"  • {update['type']}: {update['id'][:8]}... -> {update['new_status']} (applied {applied_time})")
        
    except Exception as e:
        click.echo(f"Error getting update statistics: {e}", err=True)
        raise click.Abort()


@updates.command()
@click.confirmation_option(prompt='Are you sure you want to clear all updates?')
def clear():
    """Clear all tracked updates (both pending and applied).
    
    This removes all status update tracking. Use with caution.
    """
    try:
        # Find .iriusRisk directory
        iriusrisk_dir = Path.cwd() / '.iriusRisk'
        if not iriusrisk_dir.exists():
            click.echo("No .iriusRisk directory found. Run 'iriusrisk sync' first.", err=True)
            raise click.Abort()
        
        tracker = get_update_tracker(iriusrisk_dir)
        cleared_count = tracker.clear_all_updates()
        
        click.echo(f"✅ Cleared {cleared_count} tracked updates")
        
    except Exception as e:
        click.echo(f"Error clearing updates: {e}", err=True)
        raise click.Abort()


@updates.command()
@click.confirmation_option(prompt='Are you sure you want to clear applied updates?')
def cleanup():
    """Clear only applied updates, keeping pending ones.
    
    This removes successfully applied updates from the tracking file
    while preserving any pending updates for retry.
    """
    try:
        # Find .iriusRisk directory
        iriusrisk_dir = Path.cwd() / '.iriusRisk'
        if not iriusrisk_dir.exists():
            click.echo("No .iriusRisk directory found. Run 'iriusrisk sync' first.", err=True)
            raise click.Abort()
        
        tracker = get_update_tracker(iriusrisk_dir)
        cleared_count = tracker.clear_applied_updates()
        
        if cleared_count > 0:
            click.echo(f"✅ Cleaned up {cleared_count} applied updates")
        else:
            click.echo("No applied updates to clean up")
        
        # Show remaining stats
        stats = tracker.get_stats()
        if stats['pending_updates'] > 0:
            click.echo(f"📝 {stats['pending_updates']} pending updates remain")
        
    except Exception as e:
        click.echo(f"Error cleaning up updates: {e}", err=True)
        raise click.Abort()
