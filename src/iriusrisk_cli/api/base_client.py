"""Base API client with shared HTTP and authentication functionality."""

import requests
import json
import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from ..config import Config
from ..utils.logging_config import log_api_request


class BaseApiClient:
    """Base API client providing shared HTTP and authentication functionality."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the base API client with configuration.
        
        Args:
            config: Configuration instance (creates new one if not provided)
        """
        if config is None:
            config = Config()
        
        self._config = config
        self.base_url = config.api_base_url
        self.v1_base_url = config.api_v1_base_url
        self.session = requests.Session()
        self.session.headers.update({
            'api-token': config.api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json, application/hal+json'
        })
        
        # Set up logging
        self.logger = logging.getLogger(f"iriusrisk_cli.api.{self.__class__.__name__}")
        
        # Configure SSL/TLS verification
        self.verify_ssl = config.verify_ssl
        self.ca_bundle = config.ca_bundle
        
        # Log SSL configuration
        if not self.verify_ssl:
            self.logger.warning(
                "⚠️  SSL CERTIFICATE VERIFICATION IS DISABLED ⚠️\n"
                "This is insecure and should only be used for testing/debugging.\n"
                "Your connection is vulnerable to man-in-the-middle attacks."
            )
        elif self.ca_bundle:
            self.logger.info(f"Using custom CA bundle: {self.ca_bundle}")
            # Validate CA bundle file exists
            if not Path(self.ca_bundle).exists():
                raise ValueError(
                    f"CA bundle file not found: {self.ca_bundle}\n"
                    "Please verify the path is correct and the file exists."
                )
        
        # Set up response logging
        self.log_responses = os.getenv('IRIUS_LOG_RESPONSES', '').lower() in ('true', '1', 'yes')
        if self.log_responses:
            self.log_dir = Path('captured_responses')
            self.log_dir.mkdir(exist_ok=True)
            self.logger.info(f"API Response logging enabled - saving to {self.log_dir}")
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers for logging by masking sensitive values.
        
        Args:
            headers: Dictionary of headers to sanitize
            
        Returns:
            Dictionary with sensitive headers masked
        """
        sensitive_headers = {'api-token', 'authorization', 'cookie', 'set-cookie'}
        sanitized = {}
        
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = '***MASKED***'
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_verify_param(self):
        """Get the verify parameter for requests.
        
        Returns:
            False to disable verification, path to CA bundle, or True for default
        """
        if not self.verify_ssl:
            return False
        elif self.ca_bundle:
            return self.ca_bundle
        else:
            return True
    
    def _should_retry(self, response: requests.Response, attempt: int, max_retries: int = 3) -> bool:
        """Determine if a request should be retried based on response.
        
        Args:
            response: HTTP response object
            attempt: Current attempt number (1-based)
            max_retries: Maximum number of retries allowed
            
        Returns:
            True if request should be retried, False otherwise
        """
        if attempt >= max_retries:
            return False
        
        # Retry on server errors (5xx) and rate limiting (429)
        if response.status_code >= 500 or response.status_code == 429:
            return True
        
        return False
    
    def _get_retry_delay(self, response: requests.Response, attempt: int) -> float:
        """Calculate delay before retry.
        
        Args:
            response: HTTP response object
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Check for Retry-After header
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        
        # Exponential backoff: 1s, 2s, 4s, etc.
        return min(2 ** (attempt - 1), 60)  # Cap at 60 seconds
    
    def _make_request_with_retry(self, method: str, endpoint: str, base_url: Optional[str] = None, max_retries: int = 3, **kwargs) -> requests.Response:
        """Make a request with retry logic and logging.
        
        Args:
            method: HTTP method
            endpoint: API endpoint path
            base_url: Base URL to use
            max_retries: Maximum number of retries
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If all retries fail
        """
        if base_url is None:
            base_url = self.base_url
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        last_exception = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Add default timeout if not specified
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = 30
                
                # Add SSL verification setting if not explicitly provided
                if 'verify' not in kwargs:
                    kwargs['verify'] = self._get_verify_param()
                
                if attempt > 1:
                    self.logger.info(f"Retry attempt {attempt}/{max_retries} for {method} {endpoint}")
                
                response = self.session.request(method, url, **kwargs)
                
                # Check if we should retry
                if not response.ok and self._should_retry(response, attempt, max_retries):
                    delay = self._get_retry_delay(response, attempt)
                    
                    if response.status_code == 429:
                        self.logger.warning(f"Rate limited (429) on {method} {endpoint}, retrying in {delay}s")
                    elif response.status_code >= 500:
                        self.logger.warning(f"Server error ({response.status_code}) on {method} {endpoint}, retrying in {delay}s")
                    
                    time.sleep(delay)
                    continue
                
                # Success or non-retryable error
                return response
                
            except requests.RequestException as e:
                last_exception = e
                if attempt < max_retries:
                    delay = self._get_retry_delay(None, attempt) if hasattr(e, 'response') and e.response else 2 ** (attempt - 1)
                    self.logger.warning(f"Request failed on attempt {attempt}/{max_retries}: {e}, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
        
        # This shouldn't be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise requests.RequestException(f"Request failed after {max_retries} attempts")
    
    def _log_response(self, method: str, url: str, request_kwargs: Dict[str, Any], response: requests.Response):
        """Log API request and response to file."""
        if not self.log_responses:
            return
            
        try:
            # Extract endpoint info
            if '/api/v1' in url:
                path = url.split('/api/v1')[1]
                api_version = 'v1'
            elif '/api/v2' in url:
                path = url.split('/api/v2')[1]
                api_version = 'v2'
            else:
                return  # Skip non-API URLs
            
            # Replace UUIDs with placeholders
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            pattern = re.sub(uuid_pattern, '{id}', path, flags=re.IGNORECASE)
            
            # Prepare response data
            response_data = None
            if response.text:
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = response.text
            
            # Prepare request data
            request_data = None
            if 'json' in request_kwargs:
                request_data = request_kwargs['json']
            elif 'data' in request_kwargs:
                request_data = request_kwargs['data']
            
            # Create capture record
            capture_record = {
                'timestamp': datetime.now().isoformat(),
                'method': method,
                'url': url,
                'endpoint_pattern': pattern,
                'api_version': api_version,
                'request': {
                    'headers': dict(response.request.headers) if response.request else {},
                    'body': request_data
                },
                'response': {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'body': response_data
                }
            }
            
            # Generate filename
            method_lower = method.lower()
            pattern_clean = pattern.replace('/', '_').replace('{id}', 'id').strip('_')
            if not pattern_clean:
                pattern_clean = 'root'
            
            timestamp = datetime.now().strftime('%H%M%S')
            filename = f"{api_version}_{method_lower}_{pattern_clean}_{response.status_code}_{timestamp}.json"
            
            # Save to file
            filepath = self.log_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(capture_record, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Response captured: {method} {pattern} -> {filename}")
            
        except Exception as e:
            self.logger.error(f"Error logging response: {e}")
    
    def _make_request(self, method: str, endpoint: str, base_url: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Make a request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            base_url: Base URL to use (defaults to v2 API)
            **kwargs: Additional arguments for requests
            
        Returns:
            JSON response data
            
        Raises:
            requests.RequestException: If the request fails
        """
        if base_url is None:
            base_url = self.base_url
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Log request start
        self.logger.debug(f"API request: {method} {endpoint}")
        
        # Merge any additional headers with session headers
        if 'headers' in kwargs:
            headers = self.session.headers.copy()
            headers.update(kwargs['headers'])
            kwargs['headers'] = headers
        
        # Log request details (sanitized)
        if self.logger.isEnabledFor(logging.DEBUG):
            sanitized_headers = self._sanitize_headers(kwargs.get('headers', self.session.headers))
            self.logger.debug(f"Request headers: {sanitized_headers}")
            
            # Log request body if present
            if 'json' in kwargs:
                self.logger.debug(f"Request body (JSON): {kwargs['json']}")
            elif 'data' in kwargs:
                self.logger.debug(f"Request body (data): {kwargs['data']}")
        
        start_time = time.time()
        response = None
        
        try:
            # Add default timeout if not specified
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            response = self.session.request(method, url, **kwargs)
            response_time = time.time() - start_time
            
            # Log successful response
            log_api_request(
                self.logger,
                method=method,
                url=url,
                status_code=response.status_code,
                response_time=response_time
            )
            
            # Log response details
            if self.logger.isEnabledFor(logging.DEBUG):
                content_length = len(response.content) if response.content else 0
                self.logger.debug(f"Response: {response.status_code} ({response_time:.3f}s, {content_length} bytes)")
                
                # Log response headers (sanitized)
                sanitized_response_headers = self._sanitize_headers(dict(response.headers))
                self.logger.debug(f"Response headers: {sanitized_response_headers}")
            
            response.raise_for_status()
            
            # Log the response if enabled
            self._log_response(method, url, kwargs, response)
            
            # Handle empty responses
            if not response.text.strip():
                return {}
            
            return response.json()
            
        except requests.RequestException as e:
            response_time = time.time() - start_time
            
            # Log failed request
            status_code = response.status_code if response else None
            log_api_request(
                self.logger,
                method=method,
                url=url,
                status_code=status_code,
                response_time=response_time,
                error=e
            )
            
            # Let the original exceptions bubble up unchanged for better error handling
            raise
    
    def _make_request_raw(self, method: str, endpoint: str, base_url: Optional[str] = None, **kwargs) -> str:
        """Make a request to the API and return raw text response.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            base_url: Base URL to use (defaults to v2 API)
            **kwargs: Additional arguments for requests
            
        Returns:
            Raw response text
            
        Raises:
            requests.RequestException: If the request fails
        """
        if base_url is None:
            base_url = self.base_url
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Log request start
        self.logger.debug(f"API request (raw): {method} {endpoint}")
        start_time = time.time()
        response = None
        
        try:
            # Add default timeout if not specified
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            # Add SSL verification setting if not explicitly provided
            if 'verify' not in kwargs:
                kwargs['verify'] = self._get_verify_param()
            response = self.session.request(method, url, **kwargs)
            response_time = time.time() - start_time
            
            # Log successful response
            log_api_request(
                self.logger,
                method=method,
                url=url,
                status_code=response.status_code,
                response_time=response_time
            )
            
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            response_time = time.time() - start_time
            status_code = response.status_code if response else None
            
            # Log failed request
            log_api_request(
                self.logger,
                method=method,
                url=url,
                status_code=status_code,
                response_time=response_time,
                error=e
            )
            
            # Re-raise the original exception without modifying it
            # This preserves the original error information for proper handling
            # by the error handling layer which will provide user-friendly messages
            raise
    
    def _make_request_binary(self, method: str, endpoint: str, base_url: Optional[str] = None, **kwargs) -> bytes:
        """Make a request to the API and return binary response.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            base_url: Base URL to use (defaults to v2 API)
            **kwargs: Additional arguments for requests
            
        Returns:
            Binary response content
            
        Raises:
            requests.RequestException: If the request fails
        """
        if base_url is None:
            base_url = self.base_url
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Log request start
        self.logger.debug(f"API request (binary): {method} {endpoint}")
        start_time = time.time()
        response = None
        
        try:
            # Add default timeout if not specified
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            # Add SSL verification setting if not explicitly provided
            if 'verify' not in kwargs:
                kwargs['verify'] = self._get_verify_param()
            response = self.session.request(method, url, **kwargs)
            response_time = time.time() - start_time
            
            # Log successful response
            log_api_request(
                self.logger,
                method=method,
                url=url,
                status_code=response.status_code,
                response_time=response_time
            )
            
            # Log binary response size
            if self.logger.isEnabledFor(logging.DEBUG):
                content_length = len(response.content) if response.content else 0
                self.logger.debug(f"Binary response: {response.status_code} ({response_time:.3f}s, {content_length} bytes)")
            
            response.raise_for_status()
            return response.content
            
        except requests.RequestException as e:
            response_time = time.time() - start_time
            status_code = response.status_code if response else None
            
            # Log failed request
            log_api_request(
                self.logger,
                method=method,
                url=url,
                status_code=status_code,
                response_time=response_time,
                error=e
            )
            
            # Re-raise the original exception without modifying it
            # This preserves the original error information for proper handling
            # by the error handling layer which will provide user-friendly messages
            raise
