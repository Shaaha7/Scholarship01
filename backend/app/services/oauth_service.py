"""
OAuth 2.0 Service – Google SSO Integration
===========================================
Provides OAuth 2.0 authentication flow with Google.
"""
import logging
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth 2.0 service for Google SSO."""
    
    def __init__(self):
        self.google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        self.google_client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        self.google_redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', 'http://localhost:3000/auth/callback/google')
    
    def get_google_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for Google OAuth
        """
        if not self.google_client_id:
            logger.warning("Google OAuth not configured - missing client ID")
            return ""
        
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        }
        
        if state:
            params["state"] = state
        
        # Build URL with parameters
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_str}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from Google OAuth callback
            
        Returns:
            Dictionary containing access_token, refresh_token, etc.
        """
        if not self.google_client_id or not self.google_client_secret:
            raise ValueError("Google OAuth not configured")
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.google_redirect_uri,
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()
    
    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google using access token.
        
        Args:
            access_token: Google OAuth access token
            
        Returns:
            Dictionary containing user information (id, email, name, picture, etc.)
        """
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def verify_google_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify Google ID token (alternative to code flow).
        
        Args:
            id_token: Google ID token
            
        Returns:
            Decoded token payload
        """
        # In production, use Google's token verification endpoint
        # For now, this is a placeholder
        verify_url = "https://oauth2.googleapis.com/tokeninfo"
        params = {"id_token": id_token}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(verify_url, params=params)
            response.raise_for_status()
            return response.json()


# Global OAuth service instance
oauth_service = OAuthService()
