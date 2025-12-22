"""Unit tests for the update tracking functionality."""

import pytest
import tempfile
import json
from pathlib import Path

from src.iriusrisk_cli.utils.updates import UpdateTracker, get_update_tracker


class TestUpdateTrackerThreatStates:
    """Test threat state validation in UpdateTracker."""
    
    def test_track_threat_update_valid_accept(self):
        """Test tracking threat update with valid 'accept' status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            result = tracker.track_threat_update(
                threat_id='threat-123',
                status='accept',
                reason='Risk accepted after review'
            )
            
            assert result is True
            pending = tracker.get_pending_updates()
            assert len(pending) == 1
            assert pending[0]['new_status'] == 'accept'
    
    def test_track_threat_update_valid_expose(self):
        """Test tracking threat update with valid 'expose' status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            result = tracker.track_threat_update(
                threat_id='threat-123',
                status='expose',
                reason='Leaving threat exposed'
            )
            
            assert result is True
            pending = tracker.get_pending_updates()
            assert len(pending) == 1
            assert pending[0]['new_status'] == 'expose'
    
    def test_track_threat_update_valid_not_applicable(self):
        """Test tracking threat update with valid 'not-applicable' status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            result = tracker.track_threat_update(
                threat_id='threat-123',
                status='not-applicable',
                reason='Does not apply to our architecture'
            )
            
            assert result is True
            pending = tracker.get_pending_updates()
            assert len(pending) == 1
            assert pending[0]['new_status'] == 'not-applicable'
    
    def test_track_threat_update_valid_undo_not_applicable(self):
        """Test tracking threat update with valid 'undo-not-applicable' status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            result = tracker.track_threat_update(
                threat_id='threat-123',
                status='undo-not-applicable',
                reason='Reverting previous decision'
            )
            
            assert result is True
            pending = tracker.get_pending_updates()
            assert len(pending) == 1
            assert pending[0]['new_status'] == 'undo-not-applicable'
    
    def test_track_threat_update_invalid_mitigate(self):
        """Test that 'mitigate' status is rejected with helpful error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            with pytest.raises(ValueError) as exc_info:
                tracker.track_threat_update(
                    threat_id='threat-123',
                    status='mitigate',
                    reason='Trying to mitigate'
                )
            
            error_message = str(exc_info.value)
            assert 'auto-calculated' in error_message.lower()
            assert 'countermeasures' in error_message.lower()
    
    def test_track_threat_update_invalid_partly_mitigate(self):
        """Test that 'partly-mitigate' status is rejected with helpful error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            with pytest.raises(ValueError) as exc_info:
                tracker.track_threat_update(
                    threat_id='threat-123',
                    status='partly-mitigate',
                    reason='Trying to partly mitigate'
                )
            
            error_message = str(exc_info.value)
            assert 'auto-calculated' in error_message.lower()
            assert 'countermeasures' in error_message.lower()
    
    def test_track_threat_update_invalid_hidden(self):
        """Test that 'hidden' status is rejected with helpful error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            with pytest.raises(ValueError) as exc_info:
                tracker.track_threat_update(
                    threat_id='threat-123',
                    status='hidden',
                    reason='Trying to hide'
                )
            
            error_message = str(exc_info.value)
            assert 'auto-calculated' in error_message.lower()
    
    def test_track_threat_update_invalid_unknown_status(self):
        """Test that unknown status is rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            with pytest.raises(ValueError) as exc_info:
                tracker.track_threat_update(
                    threat_id='threat-123',
                    status='invalid-status',
                    reason='Testing invalid status'
                )
            
            error_message = str(exc_info.value)
            assert 'invalid' in error_message.lower()
    
    def test_track_threat_update_case_insensitive(self):
        """Test that status validation is case-insensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            # Test uppercase
            result = tracker.track_threat_update(
                threat_id='threat-123',
                status='ACCEPT',
                reason='Risk accepted'
            )
            
            assert result is True
            pending = tracker.get_pending_updates()
            assert len(pending) == 1
            assert pending[0]['new_status'] == 'accept'  # Should be lowercased
    
    def test_track_threat_update_with_comment(self):
        """Test tracking threat update with comment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            result = tracker.track_threat_update(
                threat_id='threat-123',
                status='accept',
                reason='Risk accepted',
                comment='<p>Detailed explanation here</p>',
                context='Security review completed'
            )
            
            assert result is True
            pending = tracker.get_pending_updates()
            assert len(pending) == 1
            assert pending[0]['comment'] == '<p>Detailed explanation here</p>'
            assert pending[0]['context'] == 'Security review completed'


class TestUpdateTrackerCountermeasureStates:
    """Test countermeasure state validation in UpdateTracker."""
    
    def test_track_countermeasure_update_all_valid_states(self):
        """Test all valid countermeasure states."""
        valid_states = ['required', 'recommended', 'implemented', 'rejected', 'not-applicable']
        
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            for status in valid_states:
                tracker.track_countermeasure_update(
                    countermeasure_id=f'cm-{status}',
                    status=status,
                    reason=f'Setting to {status}'
                )
            
            pending = tracker.get_pending_updates()
            assert len(pending) == len(valid_states)
            
            # Verify all states were stored
            stored_states = [u['new_status'] for u in pending]
            assert set(stored_states) == set(valid_states)


class TestUpdateTrackerGeneral:
    """Test general UpdateTracker functionality."""
    
    def test_get_update_tracker_helper(self):
        """Test the get_update_tracker helper function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            iriusrisk_dir.mkdir()
            
            tracker = get_update_tracker(iriusrisk_dir)
            
            assert tracker is not None
            assert isinstance(tracker, UpdateTracker)
            assert tracker.iriusrisk_dir == iriusrisk_dir
    
    def test_update_tracker_persistence(self):
        """Test that updates are persisted across tracker instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            
            # First tracker - create an update
            tracker1 = UpdateTracker(iriusrisk_dir)
            tracker1.track_threat_update(
                threat_id='threat-123',
                status='accept',
                reason='Risk accepted'
            )
            
            # Second tracker - should see the same update
            tracker2 = UpdateTracker(iriusrisk_dir)
            pending = tracker2.get_pending_updates()
            
            assert len(pending) == 1
            assert pending[0]['id'] == 'threat-123'
            assert pending[0]['new_status'] == 'accept'
    
    def test_update_tracker_replaces_duplicate(self):
        """Test that updating the same threat replaces previous update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            iriusrisk_dir = Path(temp_dir) / '.iriusrisk'
            tracker = UpdateTracker(iriusrisk_dir)
            
            # First update
            tracker.track_threat_update(
                threat_id='threat-123',
                status='accept',
                reason='First decision'
            )
            
            # Second update for same threat
            tracker.track_threat_update(
                threat_id='threat-123',
                status='expose',
                reason='Changed decision'
            )
            
            pending = tracker.get_pending_updates()
            
            # Should only have one update for the threat
            assert len(pending) == 1
            assert pending[0]['new_status'] == 'expose'
            assert pending[0]['reason'] == 'Changed decision'

