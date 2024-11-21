import pytest
from app import app  # Replace with your app's import path

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Postapic!" in response.data  # Replace with your content