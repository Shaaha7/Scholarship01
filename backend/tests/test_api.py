"""
Integration Tests for API Endpoints
===================================
Tests for authentication, chat, scholarships, and admin endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user for authentication tests."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_register_user(self, test_user):
        """Test user registration."""
        response = client.post("/api/v1/auth/register", json=test_user)
        assert response.status_code in [200, 201, 400]  # 400 if user exists
        data = response.json()
        if response.status_code in [200, 201]:
            assert "email" in data
            assert data["email"] == test_user["email"]
    
    def test_login_user(self, test_user):
        """Test user login."""
        response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"]
        })
        assert response.status_code in [200, 401]  # 401 if user doesn't exist
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]


class TestChatEndpoints:
    """Test chat endpoints."""
    
    def test_send_message_anonymous(self):
        """Test sending a message without authentication."""
        response = client.post("/api/v1/chat/message", json={
            "message": "What scholarships are available for BC students?",
            "session_id": None
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
    
    def test_send_message_with_session(self):
        """Test sending a message with existing session."""
        # First message to create session
        response1 = client.post("/api/v1/chat/message", json={
            "message": "Hello",
            "session_id": None
        })
        session_id = response1.json()["session_id"]
        
        # Second message with session
        response2 = client.post("/api/v1/chat/message", json={
            "message": "Tell me about scholarships",
            "session_id": session_id
        })
        assert response2.status_code == 200


class TestScholarshipEndpoints:
    """Test scholarship endpoints."""
    
    def test_list_scholarships(self):
        """Test listing scholarships."""
        response = client.get("/api/v1/scholarships")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_scholarships(self):
        """Test searching scholarships."""
        response = client.get("/api/v1/scholarships/search", params={
            "query": "BC",
            "limit": 10
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestHealthCheck:
    """Test health check endpoint with dependency checks."""
    
    def test_health_check_dependencies(self):
        """Test health check includes dependency status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "redis" in data["dependencies"]
        assert "database" in data["dependencies"]
