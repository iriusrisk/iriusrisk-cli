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
        
        Uses POST /products/otm to create a new project. If the project already exists
        and auto_update is True, automatically falls back to updating the existing project.
        
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
                        if 'already exists' in str(error.get('message', '')).lower():
                            already_exists_error = True
                            break
                    
                    if auto_update and (already_exists_error or 'already exists' in error_msg.lower()):
                        # Extract project ID from OTM file
                        self.logger.info("Project already exists, checking if it's the same project by ref ID")
                        project_id = self._extract_project_id_from_otm(otm_file_path)
                        
                        if not project_id:
                            raise requests.RequestException(f"Project already exists but could not determine project ID from OTM file: {error_msg}")
                        
                        # Check if a project with this ref ID actually exists
                        from ..utils.api_helpers import validate_project_exists
                        exists, project_uuid = validate_project_exists(project_id, self)
                        
                        if not exists:
                            # Name conflict: project exists by name but not by ref ID
                            project_name = self._extract_project_name_from_otm(otm_file_path) or "Unknown"
                            raise requests.RequestException(
                                f"NAME CONFLICT: A project named '{project_name}' already exists in IriusRisk "
                                f"but with a different reference ID than '{project_id}' in your OTM file. "
                                f"This means you're trying to import a different project with the same name. "
                                f"\n\nTo resolve this conflict, you must either:"
                                f"\n  1. Rename your project in the OTM file to a unique name"
                                f"\n  2. Change the reference ID in your OTM file"
                                f"\n  3. Rename or delete the existing project in IriusRisk"
                            )
                        
                        # Project exists by ref ID - safe to update
                        try:
                            self.logger.info(f"Project exists with matching ref ID '{project_id}', proceeding with auto-update")
                            result = self.update_project_with_otm_file(project_id, otm_file_path)
                            result['action'] = 'updated'
                            result['ref'] = project_id  # Add ref ID for reference
                            result['uuid'] = project_uuid  # Add UUID for version operations
                            
                            # Log successful update
                            project_name = result.get('name', 'Unknown')
                            self.logger.info(f"Successfully updated project '{project_name}' (ID: {project_id})")
                            
                            return result
                        except Exception as update_error:
                            raise requests.RequestException(f"Failed to create new project (already exists) and failed to update existing project: {str(update_error)}")
                    else:
                        # Regular 400 error or auto_update disabled
                        if 'already exists' in error_msg.lower():
                            error_msg += "\n\nHint: Use auto_update=True to automatically update the existing project, or change the project name/ID in your OTM file."
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
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM import failed: {error_msg}")
    
    def _extract_project_name_from_otm(self, otm_file_path: str) -> Optional[str]:
        """Extract project name from OTM file.
        
        Args:
            otm_file_path: Path to the OTM file
            
        Returns:
            Project name if found, None otherwise
        """
        try:
            with open(otm_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try to parse as JSON first (since the file appears to be JSON)
            try:
                import json
                otm_data = json.loads(content)
                return otm_data.get('project', {}).get('name')
            except json.JSONDecodeError:
                # Try YAML
                try:
                    import yaml
                    otm_data = yaml.safe_load(content)
                    return otm_data.get('project', {}).get('name')
                except ImportError:
                    # yaml not available, try simple regex
                    import re
                    match = re.search(r'name:\s*["\']?([^"\'\n]+)["\']?', content)
                    if match:
                        return match.group(1).strip()
        except (AttributeError, KeyError, TypeError, FileNotFoundError):
            pass
        return None
    
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
    
    def import_otm_content(self, otm_content: str, auto_update: bool = True) -> Dict[str, Any]:
        """Import OTM content to create a new project or update existing one.
        
        Uses POST /products/otm to create a new project. If the project already exists
        and auto_update is True, automatically falls back to updating the existing project.
        
        Args:
            otm_content: OTM content as string
            auto_update: If True, automatically update existing project if it exists
            
        Returns:
            Project creation/update response with additional 'action' field
        """
        import requests
        
        # Log operation start
        self.logger.info(f"Importing OTM content (auto_update={auto_update})")
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token,
            'Content-Type': 'text/plain'
        })
        
        url = f"{self.v1_base_url}/products/otm"
        
        try:
            response = session.post(url, data=otm_content)
            response.raise_for_status()
            
            # Log the response if enabled
            self._log_response('POST', url, {'data': otm_content}, response)
            
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
                        if 'already exists' in str(error.get('message', '')).lower():
                            already_exists_error = True
                            break
                    
                    if auto_update and (already_exists_error or 'already exists' in error_msg.lower()):
                        # Extract project ID from OTM content
                        self.logger.info("Project already exists, checking if it's the same project by ref ID")
                        project_id = self._extract_project_id_from_content(otm_content)
                        
                        if not project_id:
                            raise requests.RequestException(f"Project already exists but could not determine project ID from OTM content: {error_msg}")
                        
                        # Check if a project with this ref ID actually exists
                        from ..utils.api_helpers import validate_project_exists
                        exists, project_uuid = validate_project_exists(project_id, self)
                        
                        if not exists:
                            # Name conflict: project exists by name but not by ref ID
                            project_name = self._extract_project_name_from_content(otm_content) or "Unknown"
                            raise requests.RequestException(
                                f"NAME CONFLICT: A project named '{project_name}' already exists in IriusRisk "
                                f"but with a different reference ID than '{project_id}' in your OTM content. "
                                f"This means you're trying to import a different project with the same name. "
                                f"\n\nTo resolve this conflict, you must either:"
                                f"\n  1. Rename your project in the OTM content to a unique name"
                                f"\n  2. Change the reference ID in your OTM content"
                                f"\n  3. Rename or delete the existing project in IriusRisk"
                            )
                        
                        # Project exists by ref ID - safe to update
                        try:
                            self.logger.info(f"Project exists with matching ref ID '{project_id}', proceeding with auto-update")
                            result = self.update_project_with_otm_content(project_id, otm_content)
                            result['action'] = 'updated'
                            result['ref'] = project_id  # Add ref ID for reference
                            result['uuid'] = project_uuid  # Add UUID for version operations
                            
                            # Log successful update
                            project_name = result.get('name', 'Unknown')
                            self.logger.info(f"Successfully updated project '{project_name}' (ID: {project_id})")
                            
                            return result
                        except Exception as update_error:
                            raise requests.RequestException(f"Failed to create new project (already exists) and failed to update existing project: {str(update_error)}")
                    else:
                        # Regular 400 error or auto_update disabled
                        if 'already exists' in error_msg.lower():
                            error_msg += "\n\nHint: Use auto_update=True to automatically update the existing project, or change the project name/ID in your OTM content."
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
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
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
    
    def _extract_project_name_from_content(self, otm_content: str) -> Optional[str]:
        """Extract project name from OTM content string.
        
        Args:
            otm_content: OTM content as string
            
        Returns:
            Project name if found, None otherwise
        """
        try:
            # Try to parse as YAML first
            try:
                import yaml
                otm_data = yaml.safe_load(otm_content)
                return otm_data.get('project', {}).get('name')
            except ImportError:
                # yaml not available, try simple regex
                match = re.search(r'name:\s*["\']([^"\']+)["\']', otm_content)
                if match:
                    return match.group(1)
        except (AttributeError, KeyError, TypeError):
            # YAML structure doesn't match expected format
            pass
        return None
    
    def update_project_with_otm_file(self, project_id: str, otm_file_path: str) -> Dict[str, Any]:
        """Update an existing project with an OTM file.
        
        NOTE: This method uses the V1 API endpoint PUT /products/otm/{project_id}
        which accepts BOTH UUIDs and reference IDs directly. Do NOT resolve the
        project_id to a UUID before calling this method - pass it through as-is.
        
        Args:
            project_id: Project UUID or reference ID (both formats accepted by V1 API)
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
                    elif e.response.status_code == 404:
                        error_msg = f"Project not found or not updateable (project may not be in draft mode, may be locked, or may be read-only). Project ID: {project_id}"
                    elif e.response.status_code == 400:
                        error_msg += f" (Bad Request - check OTM file format. Server response: {e.response.text[:200]})"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers and content type)"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    if e.response.status_code == 401:
                        error_msg += " (Check your API token configuration)"
                    elif e.response.status_code == 404:
                        error_msg = f"HTTP 404: Project not found or not updateable (project may not be in draft mode, may be locked, or may be read-only). Project ID: {project_id}"
                    elif e.response.status_code == 400:
                        error_msg += " (Bad Request - check OTM file format)"
                    elif e.response.status_code == 406:
                        error_msg += " (Not Acceptable - check request headers)"
            else:
                error_msg = str(e)
            raise requests.RequestException(f"OTM update failed: {error_msg}")
    
    def update_project_with_otm_content(self, project_id: str, otm_content: str) -> Dict[str, Any]:
        """Update an existing project with OTM content.
        
        NOTE: This method uses the V1 API endpoint PUT /products/otm/{project_id}
        which accepts BOTH UUIDs and reference IDs directly. Do NOT resolve the
        project_id to a UUID before calling this method - pass it through as-is.
        
        Args:
            project_id: Project UUID or reference ID (both formats accepted by V1 API)
            otm_content: OTM content as string
            
        Returns:
            Project update response
        """
        import requests
        
        # Create a simple session with API token authentication
        session = requests.Session()
        session.headers.update({
            'api-token': self._config.api_token,
            'Content-Type': 'text/plain'
        })
        
        url = f"{self.v1_base_url}/products/otm/{project_id}"
        
        try:
            response = session.put(url, data=otm_content)
            response.raise_for_status()
            
            # Log the response if enabled
            self._log_response('PUT', url, {'data': otm_content}, response)
            
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
        
        NOTE: This method uses the V1 API endpoint GET /products/otm/{project_id}
        which accepts BOTH UUIDs and reference IDs directly. Do NOT resolve the
        project_id to a UUID before calling this method - pass it through as-is.
        
        Args:
            project_id: Project UUID or reference ID (both formats accepted by V1 API)
            
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
