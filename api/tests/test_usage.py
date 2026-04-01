import pytest


@pytest.fixture
def model_id(client):
    r = client.post(
        "/api/v1/models/",
        json={"name": "test-model", "provider": "acme", "cost_per_input_token": 0.001, "cost_per_output_token": 0.002},
    )
    return r.json()["id"]


@pytest.fixture
def project_id(client):
    r = client.post("/api/v1/projects/", json={"name": "test-project", "team": "eng"})
    return r.json()["id"]


def test_create_usage_record(client, model_id):
    payload = {"model_id": model_id, "input_tokens": 100, "output_tokens": 50, "latency_ms": 320.5}
    response = client.post("/api/v1/usage/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["model_id"] == model_id
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50
    # cost = 100 * 0.001 + 50 * 0.002 = 0.1 + 0.1 = 0.2
    assert abs(data["cost"] - 0.2) < 1e-9


def test_create_usage_record_invalid_model(client):
    response = client.post("/api/v1/usage/", json={"model_id": 9999, "input_tokens": 10})
    assert response.status_code == 404


def test_list_usage_records_empty(client):
    response = client.get("/api/v1/usage/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_usage_records(client, model_id):
    client.post("/api/v1/usage/", json={"model_id": model_id, "input_tokens": 10})
    client.post("/api/v1/usage/", json={"model_id": model_id, "input_tokens": 20})
    response = client.get("/api/v1/usage/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_usage_by_model(client, model_id):
    r2 = client.post("/api/v1/models/", json={"name": "other-model", "provider": "acme"})
    other_model_id = r2.json()["id"]
    client.post("/api/v1/usage/", json={"model_id": model_id, "input_tokens": 10})
    client.post("/api/v1/usage/", json={"model_id": other_model_id, "input_tokens": 10})
    response = client.get(f"/api/v1/usage/?model_id={model_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["model_id"] == model_id


def test_usage_summary_empty(client):
    response = client.get("/api/v1/usage/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_calls"] == 0
    assert data["total_cost"] == 0.0


def test_usage_summary(client, model_id):
    client.post("/api/v1/usage/", json={"model_id": model_id, "input_tokens": 100, "output_tokens": 50, "latency_ms": 200.0, "success": True})
    client.post("/api/v1/usage/", json={"model_id": model_id, "input_tokens": 200, "output_tokens": 100, "latency_ms": 400.0, "success": False})
    response = client.get("/api/v1/usage/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_calls"] == 2
    assert data["total_input_tokens"] == 300
    assert data["total_output_tokens"] == 150
    assert abs(data["avg_latency_ms"] - 300.0) < 1e-9
    assert abs(data["success_rate"] - 0.5) < 1e-9


def test_usage_summary_filter_by_project(client, model_id, project_id):
    client.post("/api/v1/usage/", json={"model_id": model_id, "project_id": project_id, "input_tokens": 50})
    client.post("/api/v1/usage/", json={"model_id": model_id, "input_tokens": 200})
    response = client.get(f"/api/v1/usage/summary?project_id={project_id}")
    assert response.status_code == 200
    assert response.json()["total_calls"] == 1
    assert response.json()["total_input_tokens"] == 50
