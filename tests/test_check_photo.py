from pathlib import Path

TEST_FOLDER = Path("tests")
ASSETS_FOLDER = TEST_FOLDER / "assets"


def test_pipeline(test_app):
    image = ASSETS_FOLDER / "test.png"
    files = {"image": (image.name, image.open("rb"))}
    response = test_app.post("/check_photo", files=files)
    assert response.status_code == 200

    content = response.json()
    task_id = content["task_id"]
    assert task_id

    response = test_app.get(f"/check_photo/{task_id}")
    content = response.json()
    assert content == {
        "task_id": task_id,
        "task_status": "PENDING",
        "task_result": None,
    }
    assert response.status_code == 200

    while content["task_status"] == "PENDING":
        response = test_app.get(f"/check_photo/{task_id}")
        content = response.json()

    assert content["task_id"] == task_id
    assert content["task_status"] == "SUCCESS"


def test_check_photo(test_app):
    image = ASSETS_FOLDER / "test.jpg"
    files = {"image": (image.name, image.open("rb"))}
    response = test_app.post("/check_photo", files=files)
    assert response.status_code == 200

    content = response.json()
    task_id = content["task_id"]
    assert task_id


def test_check_photo_not_png_or_jpeg(test_app):
    files = {"image": ("test.txt", "text")}

    response = test_app.post("check_photo", files=files)
    assert response.status_code == 422
