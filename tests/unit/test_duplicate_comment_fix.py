"""
Test to verify that the duplicate comment fix works correctly.

This test ensures that when STDIO MCP tools apply updates immediately,
they mark them as applied, preventing sync from re-applying them.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.iriusrisk_cli.utils.updates import UpdateTracker, get_update_tracker


class TestDuplicateCommentFix:
    """Test that updates marked as applied are not re-applied by sync."""
    
    def test_update_tracker_marks_as_applied(self, tmp_path):
        """Test that mark_update_applied works correctly."""
        iriusrisk_dir = tmp_path / '.iriusrisk'
        iriusrisk_dir.mkdir()
        
        tracker = UpdateTracker(iriusrisk_dir)
        
        # Track a countermeasure update
        tracker.track_countermeasure_update(
            countermeasure_id="test-cm-123",
            status="implemented",
            reason="Test reason",
            comment="Test comment"
        )
        
        # Verify it's pending
        pending = tracker.get_pending_updates()
        assert len(pending) == 1
        assert pending[0]["id"] == "test-cm-123"
        assert pending[0]["applied"] == False
        
        # Mark as applied
        result = tracker.mark_update_applied("test-cm-123", "countermeasure")
        assert result == True
        
        # Verify it's no longer pending
        pending_after = tracker.get_pending_updates()
        assert len(pending_after) == 0
        
        # Verify it's still in all updates but marked as applied
        all_updates = tracker.get_all_updates()
        assert len(all_updates) == 1
        assert all_updates[0]["applied"] == True
        assert "applied_timestamp" in all_updates[0]
    
    def test_threat_update_marks_as_applied(self, tmp_path):
        """Test that threat updates can be marked as applied."""
        iriusrisk_dir = tmp_path / '.iriusrisk'
        iriusrisk_dir.mkdir()
        
        tracker = UpdateTracker(iriusrisk_dir)
        
        # Track a threat update
        tracker.track_threat_update(
            threat_id="test-threat-456",
            status="accept",
            reason="Test reason",
            comment="Test comment"
        )
        
        # Mark as applied
        result = tracker.mark_update_applied("test-threat-456", "threat")
        assert result == True
        
        # Verify it's no longer pending
        pending = tracker.get_pending_updates()
        assert len(pending) == 0
    
    def test_clear_applied_updates_removes_only_applied(self, tmp_path):
        """Test that clear_applied_updates only removes applied updates."""
        iriusrisk_dir = tmp_path / '.iriusrisk'
        iriusrisk_dir.mkdir()
        
        tracker = UpdateTracker(iriusrisk_dir)
        
        # Track two updates
        tracker.track_countermeasure_update(
            countermeasure_id="cm-1",
            status="implemented",
            reason="Reason 1",
            comment="Comment 1"
        )
        tracker.track_countermeasure_update(
            countermeasure_id="cm-2",
            status="implemented",
            reason="Reason 2",
            comment="Comment 2"
        )
        
        # Mark only first one as applied
        tracker.mark_update_applied("cm-1", "countermeasure")
        
        # Clear applied updates
        cleared = tracker.clear_applied_updates()
        assert cleared == 1
        
        # Verify only the non-applied one remains
        all_updates = tracker.get_all_updates()
        assert len(all_updates) == 1
        assert all_updates[0]["id"] == "cm-2"
        assert all_updates[0]["applied"] == False
    
    def test_multiple_updates_same_id_replaces_and_resets_applied(self, tmp_path):
        """Test that tracking a new update for same ID replaces old one."""
        iriusrisk_dir = tmp_path / '.iriusrisk'
        iriusrisk_dir.mkdir()
        
        tracker = UpdateTracker(iriusrisk_dir)
        
        # Track and apply an update
        tracker.track_countermeasure_update(
            countermeasure_id="cm-1",
            status="implemented",
            reason="First update",
            comment="First comment"
        )
        tracker.mark_update_applied("cm-1", "countermeasure")
        
        # Track a new update for the same ID
        tracker.track_countermeasure_update(
            countermeasure_id="cm-1",
            status="rejected",
            reason="Second update",
            comment="Second comment"
        )
        
        # Should have only one update, and it should be pending
        all_updates = tracker.get_all_updates()
        assert len(all_updates) == 1
        assert all_updates[0]["new_status"] == "rejected"
        assert all_updates[0]["reason"] == "Second update"
        assert all_updates[0]["applied"] == False  # Reset to pending
        
        pending = tracker.get_pending_updates()
        assert len(pending) == 1
    
    @patch('src.iriusrisk_cli.utils.project_discovery.find_project_root')
    def test_stdio_tool_workflow_prevents_duplicates(self, mock_find_root, tmp_path):
        """
        Integration test: Verify STDIO tool workflow prevents duplicates.
        
        This simulates:
        1. MCP STDIO tool applies update and marks as applied
        2. Sync runs and should skip the already-applied update
        """
        # Setup
        iriusrisk_dir = tmp_path / '.iriusrisk'
        iriusrisk_dir.mkdir()
        project_json = tmp_path / 'project.json'
        project_json.write_text('{"ref": "test-project"}')
        
        mock_find_root.return_value = (tmp_path, "test-project")
        
        tracker = get_update_tracker(iriusrisk_dir)
        
        # Simulate STDIO tool: track and immediately mark as applied
        tracker.track_countermeasure_update(
            countermeasure_id="cm-applied",
            status="implemented",
            reason="Applied by STDIO tool",
            comment="This was already applied"
        )
        tracker.mark_update_applied("cm-applied", "countermeasure")
        
        # Simulate sync: get pending updates
        pending = tracker.get_pending_updates()
        
        # Should be empty - sync won't re-apply it
        assert len(pending) == 0, "Sync should not see already-applied updates as pending"
        
        # Verify the update is still in the file for audit purposes
        all_updates = tracker.get_all_updates()
        assert len(all_updates) == 1
        assert all_updates[0]["applied"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

