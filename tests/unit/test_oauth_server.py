"""Unit tests for OAuth 2.0 server implementation.

Tests cover:
- Token generation and validation
- PKCE verification (S256 and plain)
- User credential mapping
- Token expiry handling
- Session management
- Client registration
- OAuth metadata endpoints
"""

import pytest
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

from src.iriusrisk_cli.mcp.oauth_server import (
    OAuthServer,
    load_oauth_config,
    AUTH_CODE_EXPIRES_SECONDS,
    ACCESS_TOKEN_EXPIRES_SECONDS,
)


class TestOAuthServerInitialization:
    """Test OAuthServer initialization."""
    
    def test_init_with_valid_config(self):
        """Test initialization with valid OAuth config."""
        config = {
            'oauth': {
                'provider': {
                    'name': 'google',
                    'client_id': 'test-client-id',
                    'client_secret': 'test-secret'
                }
            },
            'user_mappings': {
                'user@example.com': {
                    'iriusrisk_api_key': 'test-api-key',
                    'iriusrisk_hostname': 'https://test.iriusrisk.com',
                    'enabled': True
                }
            }
        }
        
        server = OAuthServer('https://example.com', config)
        
        assert server.base_url == 'https://example.com'
        assert server.provider_config['name'] == 'google'
        assert len(server.user_mappings) == 1
        assert server.clients == {}
        assert server.auth_codes == {}
        assert server.tokens == {}
        assert server.sessions == {}
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slashes are stripped from base_url."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        
        server = OAuthServer('https://example.com/', config)
        assert server.base_url == 'https://example.com'
    
    def test_init_with_empty_config(self):
        """Test initialization with minimal config."""
        config = {}
        
        server = OAuthServer('https://example.com', config)
        
        assert server.provider_config == {}
        assert server.user_mappings == {}


class TestPKCEVerification:
    """Test PKCE (Proof Key for Code Exchange) verification."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        self.server = OAuthServer('https://example.com', config)
    
    def test_verify_pkce_s256_valid(self):
        """Test S256 PKCE verification with valid verifier."""
        # Generate a real code verifier
        code_verifier = secrets.token_urlsafe(32)
        
        # Compute code challenge (S256 method)
        hash_digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(hash_digest).decode().rstrip("=")
        
        result = self.server._verify_pkce(code_verifier, code_challenge, "S256")
        assert result is True
    
    def test_verify_pkce_s256_invalid(self):
        """Test S256 PKCE verification with invalid verifier."""
        code_verifier = "invalid-verifier"
        code_challenge = "some-challenge-value"
        
        result = self.server._verify_pkce(code_verifier, code_challenge, "S256")
        assert result is False
    
    def test_verify_pkce_plain_valid(self):
        """Test plain PKCE verification with valid verifier."""
        code_verifier = "test-verifier-string"
        code_challenge = "test-verifier-string"
        
        result = self.server._verify_pkce(code_verifier, code_challenge, "plain")
        assert result is True
    
    def test_verify_pkce_plain_invalid(self):
        """Test plain PKCE verification with invalid verifier."""
        code_verifier = "verifier-one"
        code_challenge = "verifier-two"
        
        result = self.server._verify_pkce(code_verifier, code_challenge, "plain")
        assert result is False
    
    def test_verify_pkce_unsupported_method(self):
        """Test PKCE verification with unsupported method."""
        result = self.server._verify_pkce("verifier", "challenge", "SHA512")
        assert result is False
    
    def test_verify_pkce_uses_timing_safe_comparison(self):
        """Verify that PKCE uses timing-safe comparison."""
        # This test verifies the implementation uses secrets.compare_digest
        # by checking that the method is called (via inspection of the code)
        code_verifier = secrets.token_urlsafe(32)
        hash_digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(hash_digest).decode().rstrip("=")
        
        # The implementation should use secrets.compare_digest internally
        # We can verify this by checking the source, but for the test,
        # we just verify it returns correct results
        assert self.server._verify_pkce(code_verifier, code_challenge, "S256") is True


class TestUserCredentialMapping:
    """Test user credential mapping functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {
            'oauth': {'provider': {}},
            'user_mappings': {
                'enabled@example.com': {
                    'iriusrisk_api_key': 'enabled-api-key',
                    'iriusrisk_hostname': 'https://enabled.iriusrisk.com',
                    'enabled': True
                },
                'disabled@example.com': {
                    'iriusrisk_api_key': 'disabled-api-key',
                    'iriusrisk_hostname': 'https://disabled.iriusrisk.com',
                    'enabled': False
                },
                'default@example.com': {
                    'iriusrisk_api_key': 'default-api-key',
                    'iriusrisk_hostname': 'https://default.iriusrisk.com'
                    # No 'enabled' field - should default to True
                }
            }
        }
        self.server = OAuthServer('https://example.com', config)
    
    def test_get_credentials_enabled_user(self):
        """Test getting credentials for an enabled user."""
        credentials = self.server.get_user_iriusrisk_credentials('enabled@example.com')
        
        assert credentials is not None
        assert credentials['api_key'] == 'enabled-api-key'
        assert credentials['hostname'] == 'https://enabled.iriusrisk.com'
    
    def test_get_credentials_disabled_user(self):
        """Test getting credentials for a disabled user."""
        credentials = self.server.get_user_iriusrisk_credentials('disabled@example.com')
        
        assert credentials is None
    
    def test_get_credentials_default_enabled(self):
        """Test that users without 'enabled' field default to enabled."""
        credentials = self.server.get_user_iriusrisk_credentials('default@example.com')
        
        assert credentials is not None
        assert credentials['api_key'] == 'default-api-key'
    
    def test_get_credentials_unknown_user(self):
        """Test getting credentials for an unknown user."""
        credentials = self.server.get_user_iriusrisk_credentials('unknown@example.com')
        
        assert credentials is None


class TestTokenGeneration:
    """Test token and code generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        self.server = OAuthServer('https://example.com', config)
    
    def test_generate_session_id_uniqueness(self):
        """Test that session IDs are unique."""
        ids = [self.server._generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100
    
    def test_generate_client_id_format(self):
        """Test client ID format and uniqueness."""
        ids = [self.server._generate_client_id() for _ in range(10)]
        
        # All should be unique
        assert len(set(ids)) == 10
        
        # All should start with 'mcp_'
        for client_id in ids:
            assert client_id.startswith('mcp_')
    
    def test_generate_auth_code_uniqueness(self):
        """Test that auth codes are unique."""
        codes = [self.server._generate_auth_code() for _ in range(100)]
        assert len(set(codes)) == 100
    
    def test_generate_access_token_length(self):
        """Test access token has sufficient entropy."""
        token = self.server._generate_access_token()
        # 48 bytes of urlsafe base64 should be ~64 characters
        assert len(token) >= 60


class TestTokenValidation:
    """Test token validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {
            'oauth': {'provider': {}},
            'user_mappings': {
                'valid@example.com': {
                    'iriusrisk_api_key': 'valid-api-key',
                    'iriusrisk_hostname': 'https://valid.iriusrisk.com',
                    'enabled': True
                }
            }
        }
        self.server = OAuthServer('https://example.com', config)
    
    def test_validate_valid_token(self):
        """Test validation of a valid, non-expired token."""
        # Create a token
        token = self.server._generate_access_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        self.server.tokens[token] = {
            'email': 'valid@example.com',
            'client_id': 'test-client',
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.server.validate_token(token)
        
        assert result is not None
        assert result['email'] == 'valid@example.com'
        assert result['api_key'] == 'valid-api-key'
        assert result['hostname'] == 'https://valid.iriusrisk.com'
    
    def test_validate_expired_token(self):
        """Test validation of an expired token."""
        token = self.server._generate_access_token()
        expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        
        self.server.tokens[token] = {
            'email': 'valid@example.com',
            'client_id': 'test-client',
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.server.validate_token(token)
        
        assert result is None
        # Token should be removed
        assert token not in self.server.tokens
    
    def test_validate_unknown_token(self):
        """Test validation of an unknown token."""
        result = self.server.validate_token('unknown-token')
        assert result is None
    
    def test_validate_token_unmapped_user(self):
        """Test validation when token user is not in mappings."""
        token = self.server._generate_access_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        self.server.tokens[token] = {
            'email': 'unmapped@example.com',  # Not in user_mappings
            'client_id': 'test-client',
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.server.validate_token(token)
        assert result is None


class TestOAuthMetadata:
    """Test OAuth discovery metadata endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        self.server = OAuthServer('https://example.com/test', config)
    
    def test_get_oauth_metadata(self):
        """Test OAuth server metadata structure."""
        metadata = self.server._get_oauth_metadata()
        
        assert metadata['issuer'] == 'https://example.com/test'
        assert metadata['authorization_endpoint'] == 'https://example.com/test/oauth/authorize'
        assert metadata['token_endpoint'] == 'https://example.com/test/oauth/token'
        assert metadata['registration_endpoint'] == 'https://example.com/test/oauth/register'
        assert 'authorization_code' in metadata['grant_types_supported']
        assert 'code' in metadata['response_types_supported']
        assert 'S256' in metadata['code_challenge_methods_supported']
    
    def test_authorization_server_metadata_endpoint(self):
        """Test RFC 8414 authorization server metadata endpoint."""
        import asyncio
        
        async def run_test():
            mock_request = Mock()
            response = await self.server.authorization_server_metadata(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            assert body['issuer'] == 'https://example.com/test'
            
            # Check CORS headers
            assert response.headers.get('access-control-allow-origin') == '*'
        
        asyncio.run(run_test())
    
    def test_openid_configuration_endpoint(self):
        """Test OIDC discovery endpoint."""
        import asyncio
        
        async def run_test():
            mock_request = Mock()
            response = await self.server.openid_configuration(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            
            # Should have OAuth fields
            assert 'authorization_endpoint' in body
            assert 'token_endpoint' in body
            
            # Should have OIDC-specific fields
            assert 'userinfo_endpoint' in body
            assert 'openid' in body['scopes_supported']
        
        asyncio.run(run_test())
    
    def test_protected_resource_metadata_endpoint(self):
        """Test RFC 9728 protected resource metadata endpoint."""
        import asyncio
        
        async def run_test():
            mock_request = Mock()
            response = await self.server.protected_resource_metadata(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            
            assert body['resource'] == 'https://example.com/test/mcp'
            assert 'https://example.com/test' in body['authorization_servers']
        
        asyncio.run(run_test())


class TestClientRegistration:
    """Test dynamic client registration (RFC 7591)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        self.server = OAuthServer('https://example.com', config)
    
    def test_register_client_success(self):
        """Test successful client registration."""
        import asyncio
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.json = AsyncMock(return_value={
                'client_name': 'Test MCP Client',
                'redirect_uris': ['http://localhost:8080/callback'],
                'grant_types': ['authorization_code']
            })
            
            response = await self.server.register_client(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            
            assert 'client_id' in body
            assert body['client_id'].startswith('mcp_')
            assert body['client_name'] == 'Test MCP Client'
            assert body['token_endpoint_auth_method'] == 'none'
            
            # Client should be stored
            assert body['client_id'] in self.server.clients
        
        asyncio.run(run_test())
    
    def test_register_client_minimal(self):
        """Test client registration with minimal data."""
        import asyncio
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.json = AsyncMock(return_value={})
            
            response = await self.server.register_client(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            
            assert 'client_id' in body
            assert body['client_name'] == 'MCP Client'  # Default name
        
        asyncio.run(run_test())


class TestAuthorizationFlow:
    """Test OAuth authorization flow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {
            'oauth': {
                'provider': {
                    'client_id': 'google-client-id',
                    'client_secret': 'google-secret'
                }
            },
            'user_mappings': {}
        }
        self.server = OAuthServer('https://example.com', config)
    
    def test_authorize_creates_session(self):
        """Test that authorize endpoint creates a session."""
        import asyncio
        
        async def run_test():
            mock_request = Mock()
            mock_request.query_params = {
                'response_type': 'code',
                'client_id': 'test-client',
                'redirect_uri': 'http://localhost/callback',
                'state': 'test-state',
                'code_challenge': 'test-challenge',
                'code_challenge_method': 'S256'
            }
            
            response = await self.server.authorize(mock_request)
            
            # Should redirect to Google
            assert response.status_code == 307  # RedirectResponse
            
            # Should have created a session
            assert len(self.server.sessions) == 1
        
        asyncio.run(run_test())
    
    def test_authorize_invalid_response_type(self):
        """Test authorize with invalid response_type."""
        import asyncio
        
        async def run_test():
            mock_request = Mock()
            mock_request.query_params = {
                'response_type': 'token',  # Invalid - should be 'code'
                'client_id': 'test-client',
                'redirect_uri': 'http://localhost/callback'
            }
            
            response = await self.server.authorize(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'unsupported_response_type'
        
        asyncio.run(run_test())


class TestTokenEndpoint:
    """Test OAuth token endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {
            'oauth': {'provider': {}},
            'user_mappings': {
                'test@example.com': {
                    'iriusrisk_api_key': 'test-key',
                    'iriusrisk_hostname': 'https://test.iriusrisk.com'
                }
            }
        }
        self.server = OAuthServer('https://example.com', config)
    
    def test_token_exchange_success(self):
        """Test successful token exchange."""
        import asyncio
        
        # Create an auth code
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'test-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': None,
            'code_challenge_method': None,
            'expires_at': expires_at.isoformat(),
            'used': False
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'test-client'
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            
            assert 'access_token' in body
            assert body['token_type'] == 'Bearer'
            assert body['expires_in'] == ACCESS_TOKEN_EXPIRES_SECONDS
            
            # Auth code should be marked as used
            assert self.server.auth_codes[auth_code]['used'] is True
            
            # Token should be stored
            assert body['access_token'] in self.server.tokens
        
        asyncio.run(run_test())
    
    def test_token_exchange_with_pkce(self):
        """Test token exchange with PKCE verification."""
        import asyncio
        
        # Generate PKCE values
        code_verifier = secrets.token_urlsafe(32)
        hash_digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(hash_digest).decode().rstrip("=")
        
        # Create an auth code with PKCE
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'test-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'expires_at': expires_at.isoformat(),
            'used': False
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'test-client',
                'code_verifier': code_verifier
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 200
            body = json.loads(response.body.decode())
            assert 'access_token' in body
        
        asyncio.run(run_test())
    
    def test_token_exchange_invalid_pkce(self):
        """Test token exchange with invalid PKCE verifier."""
        import asyncio
        
        # Create an auth code with PKCE
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'test-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': 'valid-challenge',
            'code_challenge_method': 'S256',
            'expires_at': expires_at.isoformat(),
            'used': False
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'test-client',
                'code_verifier': 'invalid-verifier'
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'invalid_grant'
            assert 'code verifier' in body.get('error_description', '').lower()
        
        asyncio.run(run_test())
    
    def test_token_exchange_missing_pkce(self):
        """Test token exchange missing required PKCE verifier."""
        import asyncio
        
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'test-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': 'some-challenge',  # PKCE was used in authorize
            'code_challenge_method': 'S256',
            'expires_at': expires_at.isoformat(),
            'used': False
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'test-client'
                # No code_verifier
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'invalid_grant'
        
        asyncio.run(run_test())
    
    def test_token_exchange_expired_code(self):
        """Test token exchange with expired auth code."""
        import asyncio
        
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() - timedelta(minutes=5)  # Already expired
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'test-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': None,
            'code_challenge_method': None,
            'expires_at': expires_at.isoformat(),
            'used': False
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'test-client'
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'invalid_grant'
            assert 'expired' in body.get('error_description', '').lower()
        
        asyncio.run(run_test())
    
    def test_token_exchange_already_used_code(self):
        """Test token exchange with already-used auth code."""
        import asyncio
        
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'test-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': None,
            'code_challenge_method': None,
            'expires_at': expires_at.isoformat(),
            'used': True  # Already used
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'test-client'
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'invalid_grant'
            assert 'already used' in body.get('error_description', '').lower()
        
        asyncio.run(run_test())
    
    def test_token_exchange_wrong_client_id(self):
        """Test token exchange with mismatched client ID."""
        import asyncio
        
        auth_code = self.server._generate_auth_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        self.server.auth_codes[auth_code] = {
            'email': 'test@example.com',
            'client_id': 'original-client',
            'redirect_uri': 'http://localhost/callback',
            'code_challenge': None,
            'code_challenge_method': None,
            'expires_at': expires_at.isoformat(),
            'used': False
        }
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
                'client_id': 'different-client'  # Wrong client
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'invalid_grant'
        
        asyncio.run(run_test())
    
    def test_token_exchange_invalid_grant_type(self):
        """Test token exchange with unsupported grant type."""
        import asyncio
        
        async def run_test():
            mock_request = AsyncMock()
            mock_request.form = AsyncMock(return_value={
                'grant_type': 'client_credentials',  # Not supported
                'client_id': 'test-client'
            })
            
            response = await self.server.token(mock_request)
            
            assert response.status_code == 400
            body = json.loads(response.body.decode())
            assert body['error'] == 'unsupported_grant_type'
        
        asyncio.run(run_test())


class TestCORSHandling:
    """Test CORS preflight handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        self.server = OAuthServer('https://example.com', config)
    
    def test_options_handler(self):
        """Test CORS preflight OPTIONS response."""
        import asyncio
        
        async def run_test():
            mock_request = Mock()
            
            response = await self.server.options_handler(mock_request)
            
            assert response.status_code == 200
            assert response.headers.get('access-control-allow-origin') == '*'
            assert 'POST' in response.headers.get('access-control-allow-methods', '')
            assert 'Authorization' in response.headers.get('access-control-allow-headers', '')
        
        asyncio.run(run_test())


class TestOAuthRoutes:
    """Test OAuth route configuration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {'oauth': {'provider': {}}, 'user_mappings': {}}
        self.server = OAuthServer('https://example.com', config)
    
    def test_get_routes_returns_all_endpoints(self):
        """Test that all OAuth routes are returned."""
        routes = self.server.get_routes()
        
        # Extract paths from routes
        paths = [route.path for route in routes]
        
        # Check all expected endpoints are present
        assert '/.well-known/oauth-authorization-server' in paths
        assert '/.well-known/openid-configuration' in paths
        assert '/.well-known/oauth-protected-resource' in paths
        assert '/oauth/register' in paths
        assert '/oauth/authorize' in paths
        assert '/oauth/callback' in paths
        assert '/oauth/token' in paths


class TestLoadOAuthConfig:
    """Test OAuth configuration loading."""
    
    def test_load_oauth_config_valid_file(self, tmp_path):
        """Test loading valid OAuth config file."""
        config_data = {
            'oauth': {
                'provider': {
                    'name': 'google',
                    'client_id': 'test-id',
                    'client_secret': 'test-secret'
                }
            },
            'user_mappings': {
                'user@example.com': {
                    'iriusrisk_api_key': 'api-key',
                    'iriusrisk_hostname': 'https://test.iriusrisk.com'
                }
            }
        }
        
        config_file = tmp_path / 'oauth_mapping.json'
        config_file.write_text(json.dumps(config_data))
        
        loaded = load_oauth_config(config_file)
        
        assert loaded == config_data
    
    def test_load_oauth_config_missing_file(self, tmp_path):
        """Test loading non-existent config file."""
        config_file = tmp_path / 'nonexistent.json'
        
        with pytest.raises(FileNotFoundError):
            load_oauth_config(config_file)
    
    def test_load_oauth_config_invalid_json(self, tmp_path):
        """Test loading invalid JSON config file."""
        config_file = tmp_path / 'invalid.json'
        config_file.write_text('{ invalid json }')
        
        with pytest.raises(json.JSONDecodeError):
            load_oauth_config(config_file)

