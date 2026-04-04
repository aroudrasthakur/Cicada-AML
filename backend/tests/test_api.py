"""Tests for FastAPI endpoints using TestClient with mocked Supabase."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestListTransactions:
    @patch("app.api.routes_transactions.get_transactions")
    def test_returns_200(self, mock_get):
        mock_get.return_value = ([], 0)
        response = client.get("/api/transactions")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body

    @patch("app.api.routes_transactions.get_transactions")
    def test_with_pagination(self, mock_get):
        mock_get.return_value = ([], 0)
        response = client.get("/api/transactions?page=2&limit=10")
        assert response.status_code == 200


class TestHeuristicRegistry:
    @patch("app.api.routes_heuristics.get_registry_entries")
    def test_returns_list(self, mock_entries):
        mock_entries.return_value = [
            {"id": 1, "name": "CashStructuring", "environment": "traditional",
             "lens_tags": ["behavioral"], "description": "test", "data_requirements": []},
        ]
        response = client.get("/api/heuristics/registry")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)


class TestListNetworks:
    @patch("app.api.routes_networks.get_network_cases")
    def test_returns_200(self, mock_cases):
        mock_cases.return_value = ([], 0)
        response = client.get("/api/networks")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body


class TestListReports:
    @patch("app.api.routes_reports.get_reports")
    def test_returns_200(self, mock_reports):
        mock_reports.return_value = []
        response = client.get("/api/reports")
        assert response.status_code == 200
