# IriusRisk CLI - Agent Skills

This directory contains Agent Skills for the IriusRisk CLI, organized by LLM capability and use case.

## What are Agent Skills?

Agent Skills are portable, version-controlled packages that teach AI agents how to perform domain-specific tasks. They follow the [Agent Skills open standard](https://agentskills.io) and work across any agent that supports the standard.

## Directory Structure

```
skills/
├── reasoning-models/      # Complex analysis, multi-step workflows
│   ├── ci-cd-verification/
│   ├── compare-versions/
│   └── countermeasure-verification/
├── general-models/        # Standard workflows for most LLMs
│   ├── architecture-design-review/
│   ├── initialize-iriusrisk-workflow/
│   ├── analyze-source-material/
│   ├── create-threat-model/
│   ├── threats-and-countermeasures/
│   └── security-development-advisor/
├── code-focused/          # Heavy code analysis tasks
│   └── questionnaire-guidance/
└── shared/                # Reference/guidance for all models
    ├── otm-layout-guidance/
    └── otm-validation-guidance/
```

## Skills by Category

### Reasoning Models

**Best for:** Claude Sonnet, GPT-4, o1, other reasoning-capable models

These skills require complex analysis, multi-step decision making, and sophisticated interpretation:

- **ci-cd-verification** - Orchestrate comprehensive CI/CD security reviews combining version comparison, control verification, risk analysis, and reporting
- **compare-versions** - Compare threat model versions to identify architectural and security changes, interpret structured diffs
- **countermeasure-verification** - Verify security controls are correctly implemented in code by analyzing PR changes against requirements

### General Models

**Best for:** Most modern LLMs (Claude, GPT-4, Gemini, etc.)

Standard workflows that work well with most capable language models:

- **architecture-design-review** - Trigger point for architecture/design reviews, guides to check for existing threat models
- **initialize-iriusrisk-workflow** - Complete workflow instructions for all IriusRisk threat modeling operations
- **analyze-source-material** - Analyze mixed repositories (code + infrastructure + policies) to extract components for threat modeling
- **create-threat-model** - Step-by-step instructions for creating OTM files with validation and component mapping
- **threats-and-countermeasures** - Analyze IriusRisk-generated threats and countermeasures, explain findings, provide implementation guidance
- **security-development-advisor** - Help developers assess security impact and recommend threat modeling appropriately

### Code-Focused

**Best for:** Models with strong code analysis capabilities

Heavy code analysis requiring deep understanding of multiple programming languages and frameworks:

- **questionnaire-guidance** - Analyze source code to answer IriusRisk questionnaires, requires thorough code analysis across multiple languages

### Shared

**Best for:** All models (reference material)

Reference and guidance skills that provide detailed instructions for specific tasks:

- **otm-layout-guidance** - Detailed guidance on OTM component layout, positioning, and size calculations
- **otm-validation-guidance** - Validation rules for trust zones, component types, and filtering deprecated components

## Usage

### In Cursor

Skills are automatically discovered from `.cursor/skills/` in your project or `~/.cursor/skills/` globally.

To use a skill:
1. Type `/` in Agent chat
2. Search for the skill name
3. Or let the agent automatically apply it based on context

### Skill Invocation

Skills can be invoked in two ways:

1. **Automatic** (default) - Agent applies skill when relevant based on context
2. **Manual** - Type `/skill-name` to explicitly invoke

Some skills have `disable-model-invocation: true` which makes them manual-only (like traditional slash commands).

## Choosing the Right Skill

### For Architecture/Design Reviews
Start with: `architecture-design-review` → leads to `initialize-iriusrisk-workflow`

### For Creating Threat Models
Use: `create-threat-model` (after running `initialize-iriusrisk-workflow`)

### For Analyzing Threats
Use: `threats-and-countermeasures`

### For CI/CD Security Checks
Use: `ci-cd-verification` (reasoning models) or `compare-versions` (general models)

### For Code Security Reviews
Use: `countermeasure-verification` (reasoning models)

### For Improving Threat Model Accuracy
Use: `questionnaire-guidance` (code-focused models)

## Model Recommendations

### Reasoning Models (Complex Analysis)
- **Claude Opus/Sonnet** - Excellent for ci-cd-verification, compare-versions, countermeasure-verification
- **GPT-4 Turbo** - Good for multi-step workflows
- **o1/o1-mini** - Strong reasoning for complex security analysis

### General Models (Standard Workflows)
- **Claude Sonnet** - Excellent all-around, good balance of speed and capability
- **GPT-4** - Very capable for most workflows
- **Gemini Pro** - Good for standard threat modeling workflows

### Code-Focused (Heavy Analysis)
- **Claude Opus** - Best for deep code analysis (questionnaire-guidance)
- **GPT-4 Turbo** - Strong code understanding across languages
- **Codex/GPT-4 Code** - Specialized for code analysis

## Interoperability Notes

Most skills are **model-agnostic** and work across different LLMs. However:

- **Reasoning models** handle complex multi-step workflows better
- **Code-focused** skills benefit from models with strong code understanding
- **General models** work with any capable LLM

The categorization is a **recommendation**, not a hard requirement. You can use any skill with any model, but some combinations work better than others.

## Migration from Prompts

These skills were converted from the workflow prompts in `src/iriusrisk_cli/prompts/`:

| Original Prompt | New Skill | Category |
|----------------|-----------|----------|
| `ci_cd_verification.md` | `ci-cd-verification` | reasoning-models |
| `compare_versions.md` | `compare-versions` | reasoning-models |
| `countermeasure_verification.md` | `countermeasure-verification` | reasoning-models |
| `architecture_and_design_review.md` | `architecture-design-review` | general-models |
| `initialize_iriusrisk_workflow.md` | `initialize-iriusrisk-workflow` | general-models |
| `analyze_source_material.md` | `analyze-source-material` | general-models |
| `create_threat_model.md` | `create-threat-model` | general-models |
| `threats_and_countermeasures.md` | `threats-and-countermeasures` | general-models |
| `security_development_advisor.md` | `security-development-advisor` | general-models |
| `questionnaire_guidance.md` | `questionnaire-guidance` | code-focused |
| `otm_layout_guidance.md` | `otm-layout-guidance` | shared |
| `otm_validation_guidance.md` | `otm-validation-guidance` | shared |

## Contributing

When adding new skills:

1. Choose the appropriate category based on complexity and requirements
2. Follow the SKILL.md format with YAML frontmatter
3. Include clear `name` and `description` fields
4. Add `disable-model-invocation: true` if the skill should be manual-only
5. Document when to use the skill and what it does
6. Update this README with the new skill

## Learn More

- [Agent Skills Standard](https://agentskills.io)
- [Cursor Skills Documentation](https://cursor.com/docs/context/skills)
- [IriusRisk CLI Documentation](../README.md)
