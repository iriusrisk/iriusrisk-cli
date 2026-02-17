"""Project-specific API client for IriusRisk API."""

import json
import re
from typing import Dict, Any, Optional
from pathlib import Path

from .base_client import BaseApiClient
from ..config import Config


class ProjectApiClient(BaseApiClient):
    """API client for project-specific operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the project API client.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        super().__init__(config)
    
    def get_projects(self, 
                    page: int = 0, 
                    size: int = 20, 
                    include_versions: bool = False,
                    filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get all projects with optional filtering and pagination.
        
        Args:
            page: Page number (0-based)
            size: Number of items per page
            include_versions: Whether to include version information
            filter_expression: Filter expression for server-side filtering
            
        Returns:
            Paged response with projects
        """
        # Log operation start with parameters
        self.logger.info(f"Retrieving projects (page={page}, size={size}, include_versions={include_versions})")
        if filter_expression:
            self.logger.debug(f"Using filter expression: {filter_expression}")
        
        params = {
            'page': page,
            'size': size,
            'includeVersions': str(include_versions).lower()
        }
        
        if filter_expression:
            params['filter'] = filter_expression
        
        result = self._make_request('GET', '/projects', params=params)
        
        # Log results
        if result and '_embedded' in result and 'projects' in result['_embedded']:
            project_count = len(result['_embedded']['projects'])
            total_elements = result.get('page', {}).get('totalElements', 'unknown')
            self.logger.info(f"Retrieved {project_count} projects (total: {total_elements})")
        
        return result
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a specific project by ID.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            Project data
        """
        self.logger.info(f"Retrieving project: {project_id}")
        
        result = self._make_request('GET', f'/projects/{project_id}')
        
        # Log project details
        if result:
            project_name = result.get('name', 'Unknown')
            project_ref = result.get('ref', 'Unknown')
            self.logger.info(f"Retrieved project '{project_name}' (ref: {project_ref})")
        
        return result
    
    def get_project_artifacts(self, project_id: str, page: int = 0, size: int = 20) -> Dict[str, Any]:
        """Get all artifacts for a project.
        
        Args:
            project_id: Project ID or reference ID
            page: Page number (0-based)
            size: Number of artifacts per page
            
        Returns:
            Artifacts data with pagination info
        """
        try:
            endpoint = f"/projects/{project_id}/artifacts"
            params = {
                'page': page,
                'size': size
            }
            return self._make_request("GET", endpoint, params=params)
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Project '{project_id}' not found"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"API request failed: {error_msg}")
    
    def get_project_artifact_content(self, artifact_id: str, size: str = "ORIGINAL") -> Dict[str, Any]:
        """Get artifact content (image data) by artifact ID.
        
        Args:
            artifact_id: Artifact ID
            size: Image size - ORIGINAL, PREVIEW, or THUMBNAIL
            
        Returns:
            Artifact content data including base64 encoded image
        """
        try:
            endpoint = f"/projects/artifacts/{artifact_id}"
            params = {'size': size}
            return self._make_request("GET", endpoint, params=params)
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    error_msg = f"Artifact '{artifact_id}' not found"
                else:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"API request failed: {error_msg}")
    
    # OTM API methods (v1 API)
    def import_otm_file(self, otm_file_path: str, auto_update: bool = True) -> Dict[str, Any]:
        """Import an OTM file to create a new project or update existing one.
        
        Args:
            otm_file_path: Path to the OTM file to import
            auto_update: If True, automatically update existing project if it exists
            
        Returns:
            Project creation/update response with additional 'action' field
        """
        import requests
        
        # Log operation start
        self.logger.info(f"Importing OTM file: {otm_file_path} (auto_update={auto_update})")
        
        # Check file exists and log size
        otm_path = Path(otm_file_path)
        if not otm_path.exists():
            raise FileNotFoundError(f"OTM file not found: {otm_file_path}")
        
        file_size = otm_path.stat().st_size
        self.logger.debug(f"OTM file size: {file_size} bytes")
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token
        })
        
        url = f"{self.v1_base_url}/products/otm"
        
        try:
            with open(otm_file_path, 'rb') as f:
                files = {'file': f}
                response = session.post(url, files=files)
                
                # Log the response if enabled (before raise_for_status so we capture errors)
                self._log_response('POST', url, {'files': files}, response)
                
                response.raise_for_status()
                result = response.json()
                result['action'] = 'created'
                
                # Log successful creation
                project_name = result.get('name', 'Unknown')
                project_id = result.get('id', 'Unknown')
                self.logger.info(f"Successfully created project '{project_name}' (ID: {project_id})")
                
                return result
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    
                    # Check if it's a "project already exists" error
                    errors = error_data.get('errors', [])
                    already_exists_error = False
                    for error in errors:
                        if 'already exists' in error.get('message', ''):
                            already_exists_error = True
                            break
                    
                    if auto_update and (already_exists_error or 'already exists' in error_msg):
                        # Extract project ID from error message or OTM file
                        self.logger.info("Project already exists, attempting auto-update")
                        project_id = self._extract_project_id_from_otm(otm_file_path)
                        if project_id:
                            # Try to update the existing project instead
                            try:
                                self.logger.info(f"Updating existing project: {project_id}")
                                result = self.update_project_with_otm_file(project_id, otm_file_path)
                                result['action'] = 'updated'
                                
                                # Log successful update
                                project_name = result.get('name', 'Unknown')
                                self.logger.info(f"Successfully updated project '{project_name}' (ID: {project_id})")
                                
                                return result
                            except Exception as update_error:
                                raise requests.RequestException(f"Failed to create new project (already exists) and failed to update existing project: {str(update_error)}")
                        else:
                            raise requests.RequestException(f"Project already exists but could not determine project ID for update: {error_msg}")
                    else:
                        # Regular 400 error handling
                        if e.response.status_code == 400:
                            error_msg += f" (Bad Request - check OTM file format. Server response: {e.response.text[:200]})"
                        raise requests.RequestException(f"OTM import failed: {error_msg}")
                except ValueError:
                    # JSON parsing failed, fall through to general error handling
                    pass
            
            # General error handling for non-400 errors or failed JSON parsing
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers and content type)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM import failed: {error_msg}")
    
    def _extract_project_id_from_otm(self, otm_file_path: str) -> Optional[str]:
        """Extract project ID from OTM file.
        
        Args:
            otm_file_path: Path to the OTM file
            
        Returns:
            Project ID if found, None otherwise
        """
        try:
            with open(otm_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try to parse as YAML first
            try:
                import yaml
                otm_data = yaml.safe_load(content)
                return otm_data.get('project', {}).get('id')
            except ImportError:
                # yaml not available, try simple regex
                match = re.search(r'id:\s*["\']?([^"\'\s]+)["\']?', content)
                if match:
                    return match.group(1)
        except (AttributeError, KeyError, TypeError):
            # YAML structure doesn't match expected format
            pass
        return None
    
    def _modify_otm_project_id(self, otm_content: str, new_project_id: str) -> str:
        """Modify the project ID in OTM content.
        
        This method ensures that the project ID in the OTM file matches the desired project ID
        from project.json, preventing accidental creation of duplicate projects.
        
        Preserves the original format: JSON content stays JSON, YAML content stays YAML.
        
        Args:
            otm_content: OTM content as string (JSON or YAML format)
            new_project_id: The project ID to set in the OTM
            
        Returns:
            Modified OTM content with updated project ID in the original format
        """
        # Detect if content is JSON (starts with '{' after stripping whitespace)
        is_json = otm_content.strip().startswith('{')
        
        if is_json:
            try:
                otm_data = json.loads(otm_content)
                
                if 'project' not in otm_data:
                    otm_data['project'] = {}
                
                old_project_id = otm_data['project'].get('id', 'none')
                otm_data['project']['id'] = new_project_id
                
                if old_project_id != new_project_id:
                    self.logger.info(f"Overriding OTM project ID: '{old_project_id}' -> '{new_project_id}'")
                    self.logger.debug("Project ID override applied based on project.json reference_id")
                
                return json.dumps(otm_data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                self.logger.warning("Content looked like JSON but failed to parse, falling through to YAML")
        
        # YAML path
        try:
            import yaml
            otm_data = yaml.safe_load(otm_content)
            
            if 'project' not in otm_data:
                otm_data['project'] = {}
            
            old_project_id = otm_data['project'].get('id', 'none')
            otm_data['project']['id'] = new_project_id
            
            if old_project_id != new_project_id:
                self.logger.info(f"Overriding OTM project ID: '{old_project_id}' -> '{new_project_id}'")
                self.logger.debug("Project ID override applied based on project.json reference_id")
            
            return yaml.dump(otm_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except ImportError:
            # yaml not available, use regex-based approach
            self.logger.warning("PyYAML not available, using regex-based OTM modification (less reliable)")
            
            # Find the project.id line and replace it
            # Match patterns like: id: "value", id: 'value', id: value
            pattern = r'(project:\s*\n(?:[^\n]*\n)*?\s+)id:\s*["\']?[^"\'\n]+["\']?'
            replacement = r'\1id: "' + new_project_id + '"'
            
            modified = re.sub(pattern, replacement, otm_content, count=1, flags=re.MULTILINE)
            
            if modified == otm_content:
                self.logger.warning("Failed to modify project ID in OTM content using regex")
            else:
                self.logger.info(f"Modified OTM project ID to '{new_project_id}' using regex")
            
            return modified
    
    def import_otm_content(self, otm_content: str, auto_update: bool = True) -> Dict[str, Any]:
        """Import OTM content to create a new project or update existing one.
        
        Uses multipart file upload (same as import_otm_file) to ensure the
        IriusRisk API processes the OTM content correctly.
        
        Args:
            otm_content: OTM content as string
            auto_update: If True, automatically update existing project if it exists
            
        Returns:
            Project creation/update response with additional 'action' field
        """
        import io
        import requests
        
        self.logger.info(f"Importing OTM content ({len(otm_content)} bytes, auto_update={auto_update})")
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token
        })
        
        url = f"{self.v1_base_url}/products/otm"
        
        try:
            # Send as multipart file upload using in-memory buffer
            file_buffer = io.BytesIO(otm_content.encode('utf-8'))
            files = {'file': ('import.otm', file_buffer)}
            response = session.post(url, files=files)
            
            # Log the response if enabled
            self._log_response('POST', url, {'files': 'import.otm'}, response)
            
            response.raise_for_status()
            result = response.json()
            result['action'] = 'created'
            
            project_name = result.get('name', 'Unknown')
            project_id = result.get('id', 'Unknown')
            self.logger.info(f"Successfully created project '{project_name}' (ID: {project_id})")
            
            return result
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    
                    # Check if it's a "project already exists" error
                    errors = error_data.get('errors', [])
                    already_exists_error = False
                    for error in errors:
                        if 'already exists' in error.get('message', ''):
                            already_exists_error = True
                            break
                    
                    if auto_update and (already_exists_error or 'already exists' in error_msg):
                        # Extract project ID from OTM content
                        self.logger.info("Project already exists, attempting auto-update")
                        project_id = self._extract_project_id_from_content(otm_content)
                        if project_id:
                            # Try to update the existing project instead
                            try:
                                self.logger.info(f"Updating existing project: {project_id}")
                                result = self.update_project_with_otm_content(project_id, otm_content)
                                result['action'] = 'updated'
                                
                                project_name = result.get('name', 'Unknown')
                                self.logger.info(f"Successfully updated project '{project_name}' (ID: {project_id})")
                                
                                return result
                            except Exception as update_error:
                                raise requests.RequestException(f"Failed to create new project (already exists) and failed to update existing project: {str(update_error)}")
                        else:
                            raise requests.RequestException(f"Project already exists but could not determine project ID for update: {error_msg}")
                    else:
                        # Regular 400 error handling
                        if e.response.status_code == 400:
                            error_msg += f" (Bad Request - check OTM content format. Server response: {e.response.text[:200]})"
                        raise requests.RequestException(f"OTM import failed: {error_msg}")
                except ValueError:
                    # JSON parsing failed, fall through to general error handling
                    pass
            
            # General error handling for non-400 errors or failed JSON parsing
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers and content type)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM import failed: {error_msg}")
    
    def _extract_project_id_from_content(self, otm_content: str) -> Optional[str]:
        """Extract project ID from OTM content string.
        
        Args:
            otm_content: OTM content as string
            
        Returns:
            Project ID if found, None otherwise
        """
        try:
            # Try to parse as YAML first
            try:
                import yaml
                otm_data = yaml.safe_load(otm_content)
                return otm_data.get('project', {}).get('id')
            except ImportError:
                # yaml not available, try simple regex
                match = re.search(r'id:\s*["\']?([^"\'\s]+)["\']?', otm_content)
                if match:
                    return match.group(1)
        except (AttributeError, KeyError, TypeError):
            # YAML structure doesn't match expected format
            pass
        return None
    
    def update_project_with_otm_file(self, project_id: str, otm_file_path: str) -> Dict[str, Any]:
        """Update an existing project with an OTM file.
        
        Args:
            project_id: Project ID to update
            otm_file_path: Path to the OTM file
            
        Returns:
            Project update response
        """
        import requests
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token
        })
        
        url = f"{self.v1_base_url}/products/otm/{project_id}"
        
        try:
            with open(otm_file_path, 'rb') as f:
                files = {'file': f}
                response = session.put(url, files=files)
                response.raise_for_status()
                
                # Log the response if enabled
                self._log_response('PUT', url, {'files': files}, response)
                
                return response.json()
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 400:
                        error_msg += f" (Bad Request - check OTM file format. Server response: {e.response.text[:200]})"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers and content type)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 400:
                        error_msg += " (Bad Request - check OTM file format)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM update failed: {error_msg}")
    
    def update_project_with_otm_content(self, project_id: str, otm_content: str) -> Dict[str, Any]:
        """Update an existing project with OTM content.
        
        Uses multipart file upload (same as update_project_with_otm_file) to ensure
        the IriusRisk API processes the OTM content correctly.
        
        Args:
            project_id: Project ID to update
            otm_content: OTM content as string
            
        Returns:
            Project update response
        """
        import io
        import requests
        
        self.logger.info(f"Updating project {project_id} with OTM content ({len(otm_content)} bytes)")
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token
        })
        
        url = f"{self.v1_base_url}/products/otm/{project_id}"
        
        try:
            # Send as multipart file upload using in-memory buffer
            file_buffer = io.BytesIO(otm_content.encode('utf-8'))
            files = {'file': ('import.otm', file_buffer)}
            response = session.put(url, files=files)
            response.raise_for_status()
            
            # Log the response if enabled
            self._log_response('PUT', url, {'files': 'import.otm'}, response)
            
            return response.json()
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 400:
                        error_msg += f" (Bad Request - check OTM content format. Server response: {e.response.text[:200]})"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers and content type)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 400:
                        error_msg += " (Bad Request - check OTM content format)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM update failed: {error_msg}")
    
    def export_project_as_otm(self, project_id: str) -> str:
        """Export a project as OTM format.
        
        Args:
            project_id: Project ID to export
            
        Returns:
            OTM content as string
        """
        import requests
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token,
            'Accept': 'text/plain'
        })
        
        url = f"{self.v1_base_url}/products/otm/{project_id}"
        
        try:
            response = session.get(url)
            response.raise_for_status()
            
            # Log the response if enabled
            self._log_response('GET', url, {}, response)
            
            return response.text
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 404:
                        error_msg += f" (Project '{project_id}' not found or not accessible)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 404:
                        error_msg += f" (Project '{project_id}' not found or not accessible)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM export failed: {error_msg}")
    
    def get_diagram_content(self, project_id: str) -> str:
        """Get project diagram content in mxGraph XML format.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Diagram XML content as string (mxGraph format)
        """
        import requests
        
        self.logger.info(f"Retrieving diagram content for project: {project_id}")
        
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token,
            'Accept': 'application/xml'
        })
        
        url = f"{self.base_url}/projects/{project_id}/diagram/content"
        
        try:
            response = session.get(url)
            response.raise_for_status()
            self._log_response('GET', url, {}, response)
            self.logger.info(f"Successfully retrieved diagram content ({len(response.text)} bytes)")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Failed to retrieve diagram content: {e}")
            raise
    
    def get_diagram_content_version(self, project_id: str, version_id: str) -> str:
        """Get diagram content for a specific project version.
        
        Args:
            project_id: Project UUID
            version_id: Version UUID
            
        Returns:
            Diagram XML content as string (mxGraph format)
        """
        import requests
        
        self.logger.info(f"Retrieving diagram content for version: {version_id}")
        
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token,
            'Accept': 'application/xml'
        })
        
        url = f"{self.base_url}/projects/{project_id}/diagram/content"
        params = {'version': version_id}
        
        try:
            response = session.get(url, params=params)
            response.raise_for_status()
            self._log_response('GET', url, params, response)
            self.logger.info(f"Successfully retrieved diagram content for version ({len(response.text)} bytes)")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Failed to retrieve diagram content: {e}")
            raise

    
    def get_components(self,
                      page: int = 0,
                      size: int = 20,
                      filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get system components with optional filtering and pagination."""
        params = {
            'page': page,
            'size': size
        }

        if filter_expression:
            params['filter'] = filter_expression

        # Use v2 API for components endpoint with HAL+JSON headers
        headers = {
            'api-token': self._config.api_token,
            'Accept': 'application/hal+json'
        }

        url = f"{self.base_url.rstrip('/')}/components"

        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"API request failed: {error_msg}")

    def get_trust_zones(self,
                       page: int = 0,
                       size: int = 20,
                       filter_expression: Optional[str] = None) -> Dict[str, Any]:
        """Get system trust zones with optional filtering and pagination."""
        params = {
            'page': page,
            'size': size
        }

        if filter_expression:
            params['filter'] = filter_expression

        # Use v2 API for trust-zones endpoint with HAL+JSON headers
        headers = {
            'api-token': self._config.api_token,
            'Accept': 'application/hal+json'
        }

        url = f"{self.base_url.rstrip('/')}/trust-zones"

        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"API request failed: {error_msg}")

    def get_component(self, component_id: str) -> Dict[str, Any]:
        """Get a specific component by ID."""
        # Use v2 API for components endpoint with HAL+JSON headers
        headers = {
            'api-token': self._config.api_token,
            'Accept': 'application/hal+json'
        }

        url = f"{self.base_url.rstrip('/')}/components/{component_id}"

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            else:
                error_msg = str(e)
            raise Exception(f"API request failed: {error_msg}")
    
    def execute_rules(self, project_id: str) -> Dict[str, Any]:
        """Execute rules engine to update threat model (moves project out of draft state).
        
        This endpoint triggers the rules engine to regenerate threats and countermeasures
        based on the current project configuration. It's equivalent to clicking the
        "Update Threat Model" button in the web UI.
        
        Args:
            project_id: Project UUID or reference ID
            
        Returns:
            AsyncOperationIdResponse with operation details
            
        Raises:
            Exception: If rules execution fails
        """
        import requests
        
        self.logger.info(f"Executing rules engine for project: {project_id}")
        
        # Use v2 API endpoint for project sync (triggers rules execution)
        # POST /api/v2/projects/{project-id}/sync
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token,
            'Content-Type': 'application/json',
            'X-Irius-Async': 'true'  # Required - async mode only
        })
        
        url = f"{self.base_url}/projects/{project_id}/sync"
        
        try:
            response = session.post(url)
            response.raise_for_status()
            
            # Log the response if enabled
            self._log_response('POST', url, {}, response)
            
            result = response.json()
            self.logger.info(f"Rules execution triggered successfully for project: {project_id}")
            
            return result
            
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 403:
                        error_msg += " (Insufficient permissions - requires MODEL_UPDATE scope)"
                    elif e.response.status_code == 404:
                        error_msg += f" (Project '{project_id}' not found)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 403:
                        error_msg += " (Insufficient permissions)"
                    elif e.response.status_code == 404:
                        error_msg += f" (Project '{project_id}' not found)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"Rules execution failed: {error_msg}")