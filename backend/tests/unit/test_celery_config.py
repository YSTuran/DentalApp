from app.core.celery import celery_app


def test_mesh_validation_is_routed_to_dedicated_queue() -> None:
    assert celery_app.conf.task_default_queue == "default"
    assert celery_app.conf.task_routes["mesh.validate_file"] == {"queue": "mesh"}
