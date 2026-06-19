from MisarParserPython import detect_python_framework, parse_python_file


def test_detect_python_framework_fastapi(tmp_path):
    service = tmp_path / "user_service"
    service.mkdir()
    requirements = service / "requirements.txt"
    requirements.write_text("""fastapi
uvicorn
""", encoding="utf-8")
    (service / "main.py").write_text("""from fastapi import FastAPI
app = FastAPI()
""", encoding="utf-8")

    assert detect_python_framework(service, requirements) == "FASTAPI"


def test_parse_flask_route(tmp_path):
    service = tmp_path / "book_service"
    service.mkdir()
    app_file = service / "app.py"
    app_file.write_text("""from flask import Flask
app = Flask(__name__)

@app.route('/books', methods=['GET'])
def get_books():
    return []
""", encoding="utf-8")

    module_data = parse_python_file(app_file, service, "FLASK")

    assert module_data is not None
    assert any(function.route_path == "/books" for function in module_data.functions)
    assert any(function.http_method == "GET" for function in module_data.functions)


def test_parse_fastapi_route(tmp_path):
    service = tmp_path / "user_service"
    service.mkdir()
    app_file = service / "main.py"
    app_file.write_text("""from fastapi import FastAPI
app = FastAPI()

@app.get('/users/{user_id}')
def get_user(user_id: int):
    return {'id': user_id}
""", encoding="utf-8")

    module_data = parse_python_file(app_file, service, "FASTAPI")

    assert module_data is not None
    assert any(function.route_path == "/users/{user_id}" for function in module_data.functions)
    assert any(function.http_method == "GET" for function in module_data.functions)


def test_extract_fstring_http_call(tmp_path):
    service = tmp_path / "loan_service"
    service.mkdir()
    view_file = service / "views.py"
    view_file.write_text("""import requests
BOOK_SERVICE_URL = 'http://book_service:5000'

def reserve(book_id):
    return requests.post(f'{BOOK_SERVICE_URL}/books/{book_id}/reserve')
""", encoding="utf-8")

    module_data = parse_python_file(view_file, service, "DJANGO")
    calls = module_data.functions[0].calls

    assert any(call.call_type == "HTTP_CLIENT_CALL" for call in calls)
    assert any("/books/{book_id}/reserve" in call.endpoint_url for call in calls)
