def test_list_models_empty(client):
    response = client.get("/api/v1/models/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_model(client):
    payload = {
        "name": "gpt-4o",
        "provider": "openai",
        "cost_per_input_token": 0.000005,
        "cost_per_output_token": 0.000015,
    }
    response = client.post("/api/v1/models/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "gpt-4o"
    assert data["provider"] == "openai"
    assert data["id"] is not None


def test_create_model_duplicate(client):
    payload = {"name": "claude-3", "provider": "anthropic"}
    client.post("/api/v1/models/", json=payload)
    response = client.post("/api/v1/models/", json=payload)
    assert response.status_code == 409


def test_list_models_after_create(client):
    client.post("/api/v1/models/", json={"name": "model-a", "provider": "acme"})
    client.post("/api/v1/models/", json={"name": "model-b", "provider": "acme"})
    response = client.get("/api/v1/models/")
    assert response.status_code == 200
    assert len(response.json()) == 2
