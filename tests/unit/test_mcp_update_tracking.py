"""
Unit tests for MCP update tracking functionality.

Tests that MCP tools properly use UpdateTracker and write to correct files.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.iriusrisk_cli.utils.updates import UpdateTracker, get_update_tracker


class TestUpdateTrackerFileWriting:
    """Test that UpdateTracker writes to correct file."""
    
    def test_update_tracker_creates_updates_json(self):
        """Test that UpdateTracker creates updates.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            tracker = UpdateTracker(iriusrisk_dir)
            
            # Track an update
            tracker.track_countermeasure_update(
                countermeasure_id='cm-123',
                status='implemented',
                reason='Added validation',
                comment='<p>Implementation details</p>'
            )
            
            # Verify updates.json exists (NOT pending_updates.json)
            updates_file = iriusrisk_dir / 'updates.json'
            assert updates_file.exists(), "Should create updates.json"
            
            # Verify pending_updates.json does NOT exist
            wrong_file = iriusrisk_dir / 'pending_updates.json'
            assert not wrong_file.exists(), "Should NOT create pending_updates.json"
    
    def test_update_tracker_correct_structure(self):
        """Test that UpdateTracker uses correct data structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            tracker = UpdateTracker(iriusrisk_dir)
            tracker.track_threat_update(
                threat_id='threat-456',
                status='accept',
                reason='Risk accepted',
                comment='<p>Business justification</p>'
            )
            
            # Read file
            updates_file = iriusrisk_dir / 'updates.json'
            with open(updates_file, 'r') as f:
                data = json.load(f)
            
            # Verify structure
            assert 'updates' in data
            assert 'last_sync' in data
            assert 'metadata' in data
            assert isinstance(data['updates'], list)
            assert len(data['updates']) == 1
            
            # Verify update structure
            update = data['updates'][0]
            assert update['id'] == 'threat-456'
            assert update['type'] == 'threat'
            assert update['new_status'] == 'accept'
            assert update['reason'] == 'Risk accepted'
            assert update['comment'] == '<p>Business justification</p>'
            assert 'timestamp' in update
            assert update['applied'] is False
    
    def test_get_update_tracker_helper(self):
        """Test get_update_tracker helper function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            tracker = get_update_tracker(iriusrisk_dir)
            
            assert isinstance(tracker, UpdateTracker)
            assert tracker.updates_file == iriusrisk_dir / 'updates.json'


class TestMCPToolsUpdateTracking:
    """Test that MCP tools use UpdateTracker correctly (simplified non-async tests)."""
    
    def test_update_tracker_used_by_tools(self):
        """Test that UpdateTracker is properly imported and available to tools."""
        # This test just verifies the imports work correctly
        from src.iriusrisk_cli.utils.updates import get_update_tracker, UpdateTracker
        from src.iriusrisk_cli.mcp.tools.stdio_tools import register_stdio_tools
        
        # Verify the functions exist and are callable
        assert callable(get_update_tracker)
        assert UpdateTracker is not None
        assert callable(register_stdio_tools)
    
    def test_tools_docstrings_mention_updates_json(self):
        """Test that tool docstrings reference correct file (updates.json)."""
        from src.iriusrisk_cli.mcp.tools import stdio_tools
        import inspect
        
        # Get source code
        source = inspect.getsource(stdio_tools)
        
        # Should mention updates.json
        assert 'updates.json' in source, "Tools should reference updates.json"
        
        # Should NOT mention pending_updates.json
        assert 'pending_updates.json' not in source, "Tools should NOT reference pending_updates.json"


class TestUpdateTrackerMultipleUpdates:
    """Test UpdateTracker with multiple updates."""
    
    def test_multiple_updates_same_file(self):
        """Test that multiple updates go to same file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            tracker = UpdateTracker(iriusrisk_dir)
            
            # Track multiple updates
            tracker.track_threat_update(
                threat_id='t1',
                status='accept',
                reason='Risk 1',
                comment='<p>Comment 1</p>'
            )
            
            tracker.track_countermeasure_update(
                countermeasure_id='cm1',
                status='implemented',
                reason='Impl 1',
                comment='<p>Comment 2</p>'
            )
            
            tracker.track_threat_update(
                threat_id='t2',
                status='mitigate',
                reason='Risk 2',
                comment='<p>Comment 3</p>'
            )
            
            # Read file
            updates_file = iriusrisk_dir / 'updates.json'
            with open(updates_file, 'r') as f:
                data = json.load(f)
            
            # Should have all three updates
            assert len(data['updates']) == 3
            assert data['updates'][0]['id'] == 't1'
            assert data['updates'][1]['id'] == 'cm1'
            assert data['updates'][2]['id'] == 't2'
    
    def test_update_replaces_existing(self):
        """Test that updating same item replaces previous update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            tracker = UpdateTracker(iriusrisk_dir)
            
            # Track initial update
            tracker.track_countermeasure_update(
                countermeasure_id='cm-same',
                status='required',
                reason='Initial',
                comment='<p>First</p>'
            )
            
            # Update the same countermeasure
            tracker.track_countermeasure_update(
                countermeasure_id='cm-same',
                status='implemented',
                reason='Actually implemented',
                comment='<p>Updated comment</p>'
            )
            
            # Read file
            updates_file = iriusrisk_dir / 'updates.json'
            with open(updates_file, 'r') as f:
                data = json.load(f)
            
            # Should have only one update (the latest)
            assert len(data['updates']) == 1
            assert data['updates'][0]['id'] == 'cm-same'
            assert data['updates'][0]['new_status'] == 'implemented'
            assert data['updates'][0]['reason'] == 'Actually implemented'

