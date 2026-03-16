def test_document_lifecycle_and_diff(client):
    create_response = client.post(
        "/documents",
        json={
            "title": "Services Agreement",
            "content": "Clause 1: Payment within 30 days.\nClause 2: Confidentiality applies.",
            "author_name": "Asha Rao",
            "author_email": "asha@example.com",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    document_id = created["document"]["document_id"]

    duplicate_response = client.put(
        f"/documents/{document_id}/content",
        json={
            "content": "Clause 1: Payment within 30 days.\nClause 2: Confidentiality applies.",
            "created_by_email": "asha@example.com",
            "base_version_number": 1,
        },
    )
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["version_created"] is False

    update_response = client.put(
        f"/documents/{document_id}/content",
        json={
            "content": "Clause 1: Payment within 45 days.\nClause 2: Confidentiality applies.\nClause 3: Audit rights added.",
            "created_by_email": "asha@example.com",
            "base_version_number": 1,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["version_created"] is True
    assert updated["latest_version"]["version_number"] == 2

    versions_response = client.get(f"/documents/{document_id}/versions?page=1&page_size=10")
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()
    assert versions_payload["total_items"] == 2

    diff_response = client.get(f"/documents/{document_id}/compare?v1=1&v2=2")
    assert diff_response.status_code == 200
    diff_payload = diff_response.json()
    assert "Clause 3: Audit rights added." in diff_payload["added"]
    assert any(item["before"] == "Clause 1: Payment within 30 days." for item in diff_payload["modified"])


def test_metadata_update_does_not_create_version(client):
    create_response = client.post(
        "/documents",
        json={
            "title": "Initial Draft",
            "content": "Clause 1: Initial clause.",
            "author_name": "Riya Sen",
            "author_email": "riya@example.com",
        },
    )
    document_id = create_response.json()["document"]["document_id"]

    update_title_response = client.put(
        f"/documents/{document_id}/title",
        json={"title": "Renamed Draft"},
    )
    assert update_title_response.status_code == 200
    assert update_title_response.json()["title"] == "Renamed Draft"

    versions_response = client.get(f"/documents/{document_id}/versions")
    assert versions_response.status_code == 200
    assert versions_response.json()["total_items"] == 1
