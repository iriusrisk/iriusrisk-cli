#!/bin/bash
# IriusRisk CI/CD Security Verification Script
# Runs AI-powered security verification using Claude Code

set -e

# Color codes for output (disabled - use plain text)
RED=''
GREEN=''
YELLOW=''
BLUE=''
NC=''

# Verification prompt templates
PROMPT_DRIFT_DETECTION='You are a security analyst reviewing threat model changes.

Task: Compare the current threat model state against the baseline or most recently approved version to identify security drift.

Steps:
1. List available versions to identify the baseline
2. Use compare_versions to compare baseline against current state
3. Analyze the structured diff results
4. Generate a concise drift report

Output: Create DRIFT_REPORT.md with:
- Summary of changes (component count, threat count delta)
- Key architectural changes
- Security impact assessment
- Recommendations (approve drift / require review / remediate issues)'

PROMPT_PR_REVIEW='Acting as a CI/CD security verification bot in a pull request pipeline.

Task: Perform comprehensive security review of the code changes in this pull request:

1. Analyze the current codebase to understand existing architecture
2. Create an updated OTM file reflecting current state with any changes
3. Import the OTM to IriusRisk to update the threat model
4. Wait for IriusRisk to complete threat model processing
5. Compare updated state against the baseline version using compare_versions
6. Analyze the comparison results for security implications
7. Generate a comprehensive security report

Output: Create PR_REPORT.md with:
- Executive Summary (overall risk level, recommendation: APPROVE/REQUEST CHANGES/REJECT)
- Architecture Changes (new/modified components, dataflows, trust zones)
- New Threats Introduced (list high/critical threats with details)
- Countermeasure Changes (new required controls, removed controls)
- Risk Assessment (critical issues, potential attack scenarios)
- Required Actions Before Merge (prioritized checklist of security requirements)
- Verification Files (reference to .iriusrisk/verification/ files for detailed analysis)

Note: Use any available approved version as baseline for comparison. If multiple versions exist, prefer versions with "baseline" or "approved" in the name.'

PROMPT_CONTROL_VERIFICATION='You are reviewing security control implementations in a pull request.

Context: This PR addresses issue tracker tasks that are linked to security countermeasures in IriusRisk.

Task: Verify that security controls are correctly implemented:

1. Extract issue references from git context (branch name, commit messages, PR description)
2. Use countermeasure_verification to find countermeasures linked to those issues
3. For each linked countermeasure:
   - Read the security requirement from countermeasure description
   - Analyze the code changes in this repository
   - Verify implementation matches the requirement
   - Document evidence (files modified, configuration changes, code patterns)
   - Determine implementation status (PASSED / PARTIALLY-PASSED / FAILED)
4. Generate implementation verification report

Output: Create CONTROL_VERIFICATION_REPORT.md with:
- For each verified control:
  - Countermeasure name and requirement
  - Implementation status with clear pass/fail determination
  - Evidence found in code (specific files, line numbers, configurations)
  - Files and locations examined
  - Issues, gaps, or concerns identified
- Summary: Overall implementation quality and readiness assessment
- Recommendations: What needs to be fixed or improved

Be specific and evidence-based in your analysis.'

PROMPT_COMPREHENSIVE='Acting as a comprehensive CI/CD security verification system for deployment approval.

Task: Execute complete security verification combining drift detection, control verification, and risk analysis:

1. Use compare_versions to compare current state against baseline version
2. Use countermeasure_verification to verify control implementations (if issue tracker tasks are present)
3. Analyze overall risk delta and security posture changes
4. Provide clear deployment recommendation

Output: Create DEPLOYMENT_SECURITY_REPORT.md with:
- Executive Summary with clear GO/NO-GO recommendation
- Architectural Drift Analysis (what changed in the design)
- New Threats and Risk Changes (security implications)
- Control Implementation Verification Results (what controls were verified)
- Overall Risk Assessment (is security posture improving or degrading?)
- Blocking Issues (must be fixed before deployment)
- Required Actions (prioritized list of security requirements)
- Deployment Readiness Decision with reasoning

Provide a decisive, well-reasoned recommendation for deployment approval.'

PROMPT_AUDIT='You are conducting a security audit to understand threat model evolution.

Task: Compare two historical baseline versions to document security posture changes:

1. List available versions to identify two baselines to compare
2. Use compare_versions(baseline_version="older", target_version="newer")
3. Analyze what changed between these approved states
4. Generate an audit report

Output: Create SECURITY_AUDIT_REPORT.md with:
- Audit Context (which versions, date range)
- Architectural Evolution (how the system grew/changed)
- Security Posture Changes (more threats or fewer? Better coverage?)
- Notable Changes (major architectural shifts, new integrations)
- Trend Analysis (is security improving or degrading?)
- Recommendations (areas needing attention)'

# Help text
show_help() {
    echo -e "${BLUE}IriusRisk CI/CD Security Verification${NC}"
    cat << EOF


Usage: $(basename $0) [OPTIONS]

Options:
    -t, --type TYPE     Verification type (required)
                        Types:
                          drift       - Detect drift from baseline (compare_versions)
                          pr          - Full PR security review
                          control     - Verify control implementation
                          comprehensive - Complete security gate
                          audit       - Historical version comparison
    
    -h, --help          Show this help message

Examples:
    # Drift detection
    $(basename $0) --type drift

    # Full PR review (full security review)
    $(basename $0) --type pr

    # Control implementation verification
    $(basename $0) --type control

    # Comprehensive security review
    $(basename $0) --type comprehensive

    # Historical audit
    $(basename $0) --type audit

Requirements:
    - claude CLI must be installed and available in PATH
    - Must be run from a directory with IriusRisk project (.iriusrisk/)
    - IriusRisk CLI must be installed and configured

EOF
}

# Parse arguments
VERIFICATION_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            VERIFICATION_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate type provided
if [ -z "$VERIFICATION_TYPE" ]; then
    echo -e "${RED}Error: Verification type is required${NC}"
    show_help
    exit 1
fi

# Check for .iriusrisk directory
if [ ! -d ".iriusrisk" ]; then
    echo -e "${RED}Error: No .iriusrisk directory found in current directory${NC}"
    echo "Please run this script from a directory with an initialized IriusRisk project"
    exit 1
fi

# Check for claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: claude CLI not found${NC}"
    echo "Please install claude CLI: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Select prompt based on type
case "$VERIFICATION_TYPE" in
    drift)
        PROMPT="$PROMPT_DRIFT_DETECTION"
        DESCRIPTION="Security Drift Detection"
        OUTPUT_FILE="DRIFT_REPORT.md"
        ;;
    pr)
        PROMPT="$PROMPT_PR_REVIEW"
        DESCRIPTION="Pull Request Security Review"
        OUTPUT_FILE="PR_REPORT.md"
        ;;
    control)
        PROMPT="$PROMPT_CONTROL_VERIFICATION"
        DESCRIPTION="Control Implementation Verification"
        OUTPUT_FILE="CONTROL_VERIFICATION_REPORT.md"
        ;;
    comprehensive)
        PROMPT="$PROMPT_COMPREHENSIVE"
        DESCRIPTION="Comprehensive Security Verification"
        OUTPUT_FILE="DEPLOYMENT_SECURITY_REPORT.md"
        ;;
    audit)
        PROMPT="$PROMPT_AUDIT"
        DESCRIPTION="Security Audit - Version Comparison"
        OUTPUT_FILE="SECURITY_AUDIT_REPORT.md"
        ;;
    *)
        echo -e "${RED}Error: Invalid verification type: $VERIFICATION_TYPE${NC}"
        echo "Valid types: drift, pr, control, comprehensive, audit"
        exit 1
        ;;
esac

# Display what we're doing
echo "═══════════════════════════════════════════════════════"
echo "  IriusRisk Security Verification"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Verification Type: $DESCRIPTION"
echo "Working Directory: $(pwd)"
echo "Project: $(cat .iriusrisk/project.json 2>/dev/null | grep -o '"name": *"[^"]*"' | cut -d'"' -f4)"
echo "Expected Output: $OUTPUT_FILE"
echo ""
echo "Starting AI security analysis..."
echo ""

# Run claude with the selected prompt
claude -p "$PROMPT" --dangerously-skip-permissions --output-format stream-json --verbose

# Check exit status
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Verification complete"
    echo "📄 Report should be saved as: $OUTPUT_FILE"
else
    echo "❌ Verification failed with exit code: $EXIT_CODE"
    exit 1
fi
