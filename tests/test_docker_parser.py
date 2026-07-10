from MisarParserDocker import dockerComposeAnalysis


def test_docker_compose_analysis_reads_services_ports_and_dependencies(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("""version: '3.8'
services:
  user_service:
    build: ./user_service
    ports:
      - '8000:8000'
    depends_on:
      - user-db
  user-db:
    image: mysql:8
""", encoding="utf-8")

    containers = dockerComposeAnalysis([str(compose)], "test-project")

    assert "user_service" in containers
    assert containers["user_service"]["build"] == "./user_service"
    assert "8000:8000" in containers["user_service"]["ports"]
    assert "user-db" in containers["user_service"]["links"]
    assert containers["user-db"]["image"] == "mysql:8"
