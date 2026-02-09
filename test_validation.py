#!/usr/bin/env python3
"""Quick test script to verify OTM validation works."""

from src.iriusrisk_cli.utils.otm_utils import validate_otm_schema, get_otm_validation_summary

# Test 1: Valid OTM
valid_otm = """otmVersion: "0.1.0"
project:
  name: "Test Project"
  id: "test-project"

trustZones:
  - id: "internet"
    name: "Internet"
    risk:
      trustRating: 1

components:
  - id: "web-app"
    name: "Web Application"
    type: "web-service"
    parent:
      trustZone: "internet"

dataflows:
  - id: "flow-1"
    name: "User Request"
    source: "web-app"
    destination: "database"
"""

print("Test 1: Valid OTM")
print("=" * 50)
is_valid, errors = validate_otm_schema(valid_otm)
print(f"Valid: {is_valid}")
if errors:
    print("Errors:")
    for error in errors:
        print(f"  • {error}")
else:
    print("No errors (validation passed or skipped)")
print()

# Test 2: Invalid OTM (missing project.id)
invalid_otm = """otmVersion: "0.1.0"
project:
  name: "Test Project"

components:
  - id: "web-app"
    name: "Web Application"
    type: "web-service"
"""

print("Test 2: Invalid OTM (missing project.id and component.parent)")
print("=" * 50)
is_valid, errors = validate_otm_schema(invalid_otm)
print(f"Valid: {is_valid}")
if errors:
    print("Errors:")
    for error in errors:
        print(f"  • {error}")
else:
    print("No errors (validation passed or skipped)")
print()

# Test 3: Get summary
print("Test 3: OTM Summary")
print("=" * 50)
summary = get_otm_validation_summary(valid_otm)
print(f"Project: {summary['project_name']} (ID: {summary['project_id']})")
print(f"Trust Zones: {summary['trust_zones_count']}")
print(f"Components: {summary['components_count']}")
print(f"Dataflows: {summary['dataflows_count']}")
print(f"Threats: {summary['threats_count']}")
print(f"Mitigations: {summary['mitigations_count']}")
