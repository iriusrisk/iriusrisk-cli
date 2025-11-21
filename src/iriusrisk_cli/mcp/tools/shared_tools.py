"""Shared MCP tools available in both stdio and HTTP modes.

These tools work identically regardless of transport mode.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def register_shared_tools(mcp_server, api_client, transport_mode):
    """Register tools that work in both stdio and HTTP modes.
    
    Args:
        mcp_server: FastMCP server instance
        api_client: IriusRiskApiClient instance (or None for HTTP mode)
        transport_mode: TransportMode enum value
    """
    from ..transport import TransportMode
    from ... import __version__
    
    @mcp_server.tool()
    async def get_cli_version() -> str:
        """Get the current version of IriusRisk CLI.
        
        Returns:
            Version string of the IriusRisk CLI.
        """
        logger.info(f"Provided CLI version: {__version__}")
        return f"IriusRisk CLI version {__version__}"
    
    @mcp_server.tool()
    async def initialize_iriusrisk_workflow() -> str:
        """Initialize IriusRisk workflow and get critical usage instructions for AI assistants.
        
        MANDATORY: This tool must be called before using any other IriusRisk MCP tools.
        Provides essential workflow instructions and tool usage guidelines.
        
        Returns:
            Critical workflow instructions and tool usage guidelines for AI assistants.
        """
        logger.info("MCP tool invoked: initialize_iriusrisk_workflow")
        logger.debug("Providing workflow instructions to AI assistant")
        
        # Load appropriate instructions based on transport mode
        if transport_mode == TransportMode.HTTP:
            instructions = _load_prompt("http_workflow")
        else:
            instructions = _load_prompt("initialize_iriusrisk_workflow")
        
        logger.info("Provided critical IriusRisk workflow instructions to AI assistant")
        return _apply_prompt_customizations('initialize_iriusrisk_workflow', instructions)
    
    @mcp_server.tool()
    async def analyze_source_material() -> str:
        """Get comprehensive instructions for analyzing mixed source repositories.
        
        This tool provides AI assistants with detailed guidance on how to analyze
        repositories containing multiple source types (application code, infrastructure,
        policies, documentation) and extract all relevant components for a single,
        comprehensive threat model.
        
        Returns:
            Detailed instructions for analyzing mixed source repositories and extracting
            all component types for unified threat modeling.
        """
        logger.info("Providing source material analysis instructions via MCP")
        
        instructions = _load_prompt("analyze_source_material")
        
        logger.info("Provided source material analysis instructions to AI assistant")
        return _apply_prompt_customizations('analyze_source_material', instructions)
    
    @mcp_server.tool()
    async def create_threat_model() -> str:
        """Get comprehensive instructions for creating an IriusRisk threat model.
        
        This tool provides step-by-step instructions for AI assistants on how to
        create a complete threat model using the IriusRisk CLI workflow.
        
        Returns:
            Detailed instructions for creating threat models from source material.
        """
        instructions = _load_prompt("create_threat_model")
        logger.info("Provided CreateThreatModel instructions to AI assistant")
        return _apply_prompt_customizations('create_threat_model', instructions)
    
    @mcp_server.tool()
    async def threats_and_countermeasures() -> str:
        """Get instructions for reading and exploring threats and countermeasures data.
        
        This tool provides comprehensive instructions for AI assistants on how to
        read, analyze, and help users explore the threats and countermeasures that
        IriusRisk automatically generated for their project.
        
        Returns:
            Detailed instructions for working with threats and countermeasures data.
        """
        logger.info("Providing threats and countermeasures instructions via MCP")
        
        instructions = _load_prompt("threats_and_countermeasures")
        
        logger.info("Provided threats and countermeasures instructions to AI assistant")
        return _apply_prompt_customizations('threats_and_countermeasures', instructions)
    
    @mcp_server.tool()
    async def architecture_and_design_review() -> str:
        """Provides guidance for architecture and design reviews with optional threat modeling.
        
        **CALL THIS TOOL FOR:**
        - Architecture reviews: "Review the architecture", "Explain the system design"
        - Codebase understanding: "What does this project do?", "How does this system work?"
        - Design analysis: "Analyze the design", "Show me the components"
        - Security assessment: "Is this secure?", "What are the risks?", "Security review"
        - System documentation: "Document the architecture", "Explain the structure"
        
        This tool helps AI assistants determine whether to use existing threat models or recommend
        threat model creation based on user intent and context.
        
        Returns:
            Instructions for conducting architecture reviews and when to recommend threat modeling.
        """
        logger.info("MCP architecture_and_design_review called")
        
        guidance = _load_prompt("architecture_and_design_review")

        logger.info("Provided architecture and design review guidance")
        return _apply_prompt_customizations('architecture_and_design_review', guidance)
    
    @mcp_server.tool()
    async def security_development_advisor() -> str:
        """Provides security guidance and recommendations for development work.
        
        Call this tool when developers are:
        - Planning security-impacting changes (integrations, data handling, auth changes)
        - Asking about security implications of their work
        - Working on features that cross trust boundaries
        - Making architectural or infrastructure changes
        
        This tool helps assess security impact and recommend when threat modeling would be valuable,
        while respecting developer autonomy and workflow.
        
        Returns:
            Security assessment and guidance on when to recommend threat modeling.
        """
        guidance = _load_prompt("security_development_advisor")

        logger.info("MCP security_development_advisor called")
        return _apply_prompt_customizations('security_development_advisor', guidance)


def _load_prompt(prompt_name: str) -> str:
    """Load prompt instructions from external file.
    
    Prompts are stored in the prompts/ directory as markdown files.
    This allows easier editing and version control of AI instructions.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        
    Returns:
        The prompt content as a string
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        IOError: If the file cannot be read
    """
    prompts_dir = Path(__file__).parent.parent.parent / 'prompts'
    prompt_file = prompts_dir / f'{prompt_name}.md'
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_file}")
        raise FileNotFoundError(f"Prompt file '{prompt_name}.md' not found in {prompts_dir}")
    except IOError as e:
        logger.error(f"Error reading prompt file {prompt_file}: {e}")
        raise


def _apply_prompt_customizations(tool_name: str, base_prompt: str) -> str:
    """Apply any configured prompt customizations from project.json.
    
    This allows users to customize MCP tool prompts on a per-project basis by adding
    a 'prompts' section to their project.json file. Only works in stdio mode where
    project.json is available.
    
    Args:
        tool_name: Name of the MCP tool function
        base_prompt: The default prompt text for the tool
        
    Returns:
        The customized prompt text, or the base prompt if no customizations exist
    """
    # Import here to avoid circular dependencies
    from ...utils.project_discovery import find_project_root
    
    # Try to find project root and config
    try:
        project_root, project_config = find_project_root()
    except Exception as e:
        logger.debug(f"Could not find project root: {e}")
        return base_prompt
    
    if not project_config:
        return base_prompt
    
    customizations = project_config.get('prompts', {}).get(tool_name, {})
    
    if not customizations:
        return base_prompt
    
    # Get the .iriusrisk directory for resolving relative file paths
    if project_root:
        if isinstance(project_root, str):
            project_root = Path(project_root)
        iriusrisk_dir = project_root / '.iriusrisk'
    else:
        iriusrisk_dir = Path.cwd() / '.iriusrisk'
    
    # Handle replace first (it overrides everything)
    if 'replace' in customizations:
        logger.info(f"Applying 'replace' customization to {tool_name}")
        try:
            replacement_text = _load_prompt_text(customizations['replace'], iriusrisk_dir, 'replace')
            return replacement_text
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error(f"Error loading 'replace' customization for {tool_name}: {e}")
            raise
    
    # Apply prefix and/or postfix
    result = base_prompt
    if 'prefix' in customizations:
        logger.info(f"Applying 'prefix' customization to {tool_name}")
        try:
            prefix_text = _load_prompt_text(customizations['prefix'], iriusrisk_dir, 'prefix')
            result = prefix_text + result
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error(f"Error loading 'prefix' customization for {tool_name}: {e}")
            raise
    
    if 'postfix' in customizations:
        logger.info(f"Applying 'postfix' customization to {tool_name}")
        try:
            postfix_text = _load_prompt_text(customizations['postfix'], iriusrisk_dir, 'postfix')
            result = result + postfix_text
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.error(f"Error loading 'postfix' customization for {tool_name}: {e}")
            raise
    
    return result


def _load_prompt_text(value, iriusrisk_dir: Path, action_name: str) -> str:
    """Load prompt text from either a string or a file reference.
    
    Args:
        value: Either a string (used directly) or a dict with 'file' key (loaded from file)
        iriusrisk_dir: Path to the .iriusrisk directory (for resolving relative paths)
        action_name: Name of the action (prefix/postfix/replace) for error messages
        
    Returns:
        The prompt text as a string
        
    Raises:
        ValueError: If the value format is invalid
        FileNotFoundError: If the file doesn't exist
        IOError: If the file cannot be read
    """
    # If it's a string, use it directly
    if isinstance(value, str):
        return value
    
    # If it's a dict, expect a 'file' key
    if isinstance(value, dict):
        if 'file' not in value:
            raise ValueError(
                f"Dictionary value for '{action_name}' must contain a 'file' key. "
                f"Got: {list(value.keys())}"
            )
        
        file_path = value['file']
        if not isinstance(file_path, str):
            raise ValueError(f"File path for '{action_name}' must be a string, got: {type(file_path)}")
        
        # Convert to Path object
        path = Path(file_path)
        
        # If not absolute, make it relative to .iriusrisk directory
        if not path.is_absolute():
            path = iriusrisk_dir / path
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt file for '{action_name}' not found: {path}\n"
                f"(resolved from: {file_path})"
            )
        
        if not path.is_file():
            raise ValueError(f"Prompt path for '{action_name}' is not a file: {path}")
        
        # Read and return the file contents
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded {len(content)} characters from file: {path}")
            return content
        except IOError as e:
            logger.error(f"Error reading prompt file {path}: {e}")
            raise IOError(f"Failed to read prompt file for '{action_name}': {path}") from e
    
    # Invalid type
    raise ValueError(
        f"Prompt customization '{action_name}' must be either a string or a dict with 'file' key. "
        f"Got: {type(value)}"
    )

