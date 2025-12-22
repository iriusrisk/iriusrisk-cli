"""
Update tracking utilities for IriusRisk CLI.

This module provides functionality to track threat and countermeasure status
updates made by AI assistants, allowing for batched synchronization with IriusRisk.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UpdateTracker:
    """Manages tracking of threat and countermeasure status updates."""
    
    def __init__(self, iriusrisk_dir: Optional[Path] = None):
        """Initialize the update tracker.
        
        Args:
            iriusrisk_dir: Path to .iriusrisk directory. If None, uses current directory.
        """
        if iriusrisk_dir is None:
            iriusrisk_dir = Path.cwd() / '.iriusrisk'
        
        self.iriusrisk_dir = iriusrisk_dir
        self.updates_file = iriusrisk_dir / 'updates.json'
        
        # Ensure directory exists
        self.iriusrisk_dir.mkdir(exist_ok=True)
    
    def _load_updates(self) -> Dict[str, Any]:
        """Load updates from the updates.json file.
        
        Returns:
            Dictionary containing updates data
        """
        if not self.updates_file.exists():
            return {
                "updates": [],
                "last_sync": None,
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().isoformat()
                }
            }
        
        try:
            with open(self.updates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load updates file: {e}. Creating new one.")
            return {
                "updates": [],
                "last_sync": None,
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().isoformat()
                }
            }
    
    def _save_updates(self, data: Dict[str, Any]) -> None:
        """Save updates to the updates.json file.
        
        Args:
            data: Updates data to save
        """
        try:
            with open(self.updates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save updates file: {e}")
            raise
    
    def track_threat_update(self, threat_id: str, status: str, reason: str, context: Optional[str] = None, comment: Optional[str] = None) -> bool:
        """Track a threat status update.
        
        IMPORTANT: Understand 'accept' vs 'not-applicable':
        - accept: Threat IS REAL, but accepting the risk (compensating controls, risk tolerance)
        - not-applicable: Threat DOES NOT EXIST (false positive, doesn't apply to architecture)
        
        Args:
            threat_id: Threat UUID
            status: New status (accept, expose, not-applicable, undo-not-applicable)
                   - accept: Real threat, accepting risk (needs strong reason)
                   - expose: Leave unaddressed
                   - not-applicable: False positive, threat doesn't exist
                   - undo-not-applicable: Revert previous not-applicable
                   Note: mitigate/partly-mitigate/hidden are auto-calculated by IriusRisk
            reason: Reason for the status change
                   For accept: Explain compensating controls or why risk is acceptable
                   For not-applicable: Explain why threat doesn't apply to this system
            context: Optional context about the change
            comment: Optional detailed comment with implementation details
            
        Returns:
            True if update was tracked successfully
        """
        valid_statuses = ['accept', 'expose', 'not-applicable', 'undo-not-applicable']
        if status.lower() not in valid_statuses:
            # Provide helpful error message for commonly attempted invalid states
            if status.lower() in ['mitigate', 'partly-mitigate', 'hidden']:
                raise ValueError(
                    f"Invalid threat status: {status}. This is an auto-calculated state. "
                    f"Threats become 'mitigate' or 'partly-mitigate' automatically when countermeasures are implemented. "
                    f"Valid state transitions are: {valid_statuses}"
                )
            raise ValueError(f"Invalid threat status: {status}. Must be one of: {valid_statuses}")
        
        update_entry = {
            "id": threat_id,
            "type": "threat",
            "new_status": status.lower(),
            "reason": reason,
            "context": context,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
            "applied": False
        }
        
        data = self._load_updates()
        
        # Remove any existing update for this threat
        data["updates"] = [u for u in data["updates"] if not (u["id"] == threat_id and u["type"] == "threat")]
        
        # Add new update
        data["updates"].append(update_entry)
        
        self._save_updates(data)
        logger.info(f"Tracked threat update: {threat_id} -> {status}")
        return True
    
    def track_countermeasure_update(self, countermeasure_id: str, status: str, reason: str, context: Optional[str] = None, comment: Optional[str] = None) -> bool:
        """Track a countermeasure status update.
        
        Args:
            countermeasure_id: Countermeasure UUID
            status: New status (required, recommended, implemented, rejected, not-applicable)
            reason: Reason for the status change
            context: Optional context about the change
            comment: Optional detailed comment with implementation details
            
        Returns:
            True if update was tracked successfully
        """
        valid_statuses = ['required', 'recommended', 'implemented', 'rejected', 'not-applicable']
        if status.lower() not in valid_statuses:
            raise ValueError(f"Invalid countermeasure status: {status}. Must be one of: {valid_statuses}")
        
        update_entry = {
            "id": countermeasure_id,
            "type": "countermeasure",
            "new_status": status.lower(),
            "reason": reason,
            "context": context,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
            "applied": False
        }
        
        data = self._load_updates()
        
        # Remove any existing update for this countermeasure
        data["updates"] = [u for u in data["updates"] if not (u["id"] == countermeasure_id and u["type"] == "countermeasure")]
        
        # Add new update
        data["updates"].append(update_entry)
        
        self._save_updates(data)
        logger.info(f"Tracked countermeasure update: {countermeasure_id} -> {status}")
        return True
    
    def track_issue_creation(self, countermeasure_id: str, issue_tracker_id: Optional[str] = None) -> bool:
        """Track an issue creation request for a countermeasure.
        
        Args:
            countermeasure_id: Countermeasure UUID to create issue for
            issue_tracker_id: Optional specific issue tracker ID to use
            
        Returns:
            True if issue creation request was tracked successfully
        """
        update_entry = {
            "id": countermeasure_id,
            "type": "issue_creation",
            "issue_tracker_id": issue_tracker_id,
            "timestamp": datetime.now().isoformat(),
            "applied": False
        }
        
        data = self._load_updates()
        
        # Remove any existing issue creation request for this countermeasure
        data["updates"] = [u for u in data["updates"] 
                          if not (u.get("id") == countermeasure_id and u.get("type") == "issue_creation")]
        
        # Add the new update
        data["updates"].append(update_entry)
        
        try:
            self._save_updates(data)
            logger.info(f"Tracked issue creation request for countermeasure {countermeasure_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to track issue creation request: {e}")
            return False
    
    def get_pending_updates(self) -> List[Dict[str, Any]]:
        """Get all pending updates that haven't been applied.
        
        Returns:
            List of pending update entries
        """
        data = self._load_updates()
        return [u for u in data["updates"] if not u.get("applied", False)]
    
    def get_all_updates(self) -> List[Dict[str, Any]]:
        """Get all updates (pending and applied).
        
        Returns:
            List of all update entries
        """
        data = self._load_updates()
        return data["updates"]
    
    def mark_update_applied(self, update_id: str, update_type: str) -> bool:
        """Mark an update as applied.
        
        Args:
            update_id: ID of the threat or countermeasure
            update_type: Type of update ('threat' or 'countermeasure')
            
        Returns:
            True if update was found and marked as applied
        """
        data = self._load_updates()
        
        for update in data["updates"]:
            if update["id"] == update_id and update["type"] == update_type:
                update["applied"] = True
                update["applied_timestamp"] = datetime.now().isoformat()
                self._save_updates(data)
                logger.info(f"Marked {update_type} update as applied: {update_id}")
                return True
        
        return False
    
    def clear_applied_updates(self) -> int:
        """Remove all applied updates from the tracking file.
        
        Returns:
            Number of updates that were removed
        """
        data = self._load_updates()
        original_count = len(data["updates"])
        
        # Keep only non-applied updates
        data["updates"] = [u for u in data["updates"] if not u.get("applied", False)]
        
        removed_count = original_count - len(data["updates"])
        
        if removed_count > 0:
            self._save_updates(data)
            logger.info(f"Cleared {removed_count} applied updates")
        
        return removed_count
    
    def clear_all_updates(self) -> int:
        """Remove all updates from the tracking file.
        
        Returns:
            Number of updates that were removed
        """
        data = self._load_updates()
        count = len(data["updates"])
        
        data["updates"] = []
        data["last_sync"] = datetime.now().isoformat()
        
        self._save_updates(data)
        logger.info(f"Cleared all {count} updates")
        return count
    
    def update_last_sync(self) -> None:
        """Update the last sync timestamp."""
        data = self._load_updates()
        data["last_sync"] = datetime.now().isoformat()
        self._save_updates(data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about tracked updates.
        
        Returns:
            Dictionary with update statistics
        """
        data = self._load_updates()
        updates = data["updates"]
        
        stats = {
            "total_updates": len(updates),
            "pending_updates": len([u for u in updates if not u.get("applied", False)]),
            "applied_updates": len([u for u in updates if u.get("applied", False)]),
            "threat_updates": len([u for u in updates if u["type"] == "threat"]),
            "countermeasure_updates": len([u for u in updates if u["type"] == "countermeasure"]),
            "last_sync": data.get("last_sync"),
            "updates_file": str(self.updates_file)
        }
        
        return stats


def get_update_tracker(iriusrisk_dir: Optional[Path] = None) -> UpdateTracker:
    """Get an instance of the update tracker.
    
    Args:
        iriusrisk_dir: Path to .iriusrisk directory. If None, uses current directory.
        
    Returns:
        UpdateTracker instance
    """
    return UpdateTracker(iriusrisk_dir)
