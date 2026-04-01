def test_list_projects_empty(client):
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_project(client):
    payload = {"name": "my-project", "team": "platform", "description": "Test project"}
    response = client.post("/api/v1/projects/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-project"
    assert data["team"] == "platform"
    assert data["id"] is not None


def test_create_project_duplicate(client):
    payload = {"name": "dup-project", "team": "eng"}
    client.post("/api/v1/projects/", json=payload)
    response = client.post("/api/v1/projects/", json=payload)
    assert response.status_code == 409


def test_list_projects_after_create(client):
    client.post("/api/v1/projects/", json={"name": "proj-a", "team": "a"})
    client.post("/api/v1/projects/", json={"name": "proj-b", "team": "b"})
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert len(response.json()) == 2
