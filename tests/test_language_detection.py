from MisarParserLanguage import detect_language_scopes, format_module_display_path, strip_language_badge


def test_detect_fastapi_service(tmp_path):
    service = tmp_path / "user_service"
    service.mkdir()
    (service / "requirements.txt").write_text("""fastapi
uvicorn
""", encoding="utf-8")
    (service / "main.py").write_text("""from fastapi import FastAPI
app = FastAPI()
""", encoding="utf-8")

    scopes = detect_language_scopes(service)

    assert any(scope.language == "python" for scope in scopes)
    assert any(scope.framework == "FASTAPI" for scope in scopes)


def test_detect_spring_service(tmp_path):
    service = tmp_path / "order_service"
    src = service / "src" / "main" / "java" / "com" / "example"
    src.mkdir(parents=True)
    (service / "pom.xml").write_text("""<project><dependencies>
<dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
</dependencies></project>
""", encoding="utf-8")
    (src / "OrderApplication.java").write_text("""import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication
class OrderApplication {}
""", encoding="utf-8")

    scopes = detect_language_scopes(service)

    assert any(scope.language == "java" for scope in scopes)
    assert any(scope.framework == "SPRING" for scope in scopes)


def test_detect_mixed_java_python_service(tmp_path):
    service = tmp_path / "mixed_service"
    service.mkdir()
    (service / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (service / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (service / "pom.xml").write_text("""<project><dependencies>
<dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
</dependencies></project>
""", encoding="utf-8")
    (service / "Application.java").write_text("@SpringBootApplication\nclass Application {}\n", encoding="utf-8")

    display = format_module_display_path(service)

    assert "Python: FASTAPI" in display
    assert "Java: SPRING" in display


def test_strip_language_badge_returns_raw_path():
    raw = "/tmp/service"
    labelled = raw + " [Python: FASTAPI]"

    assert strip_language_badge(labelled) == raw
