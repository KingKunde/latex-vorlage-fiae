from pathlib import Path
import sys

from fastapi import Request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.errors import ValidationErrors
from app.web.templates.forms import build_form_redirect_url, read_form_state


def make_request(query_string: bytes) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/users/create",
            "headers": [],
            "query_string": query_string,
        }
    )


def test_form_url_plain():
    url = build_form_redirect_url("/users/create")

    assert url == "/users/create"


def test_form_url_state():
    url = build_form_redirect_url(
        "/users/create",
        validation_errors=ValidationErrors({"email": "E-Mail fehlt"}),
        values={"first_name": "Max", "organization_id": 3, "ignored": None},
    )

    assert url.startswith("/users/create?")
    assert "error=E-Mail+fehlt" in url
    assert "fe_email=E-Mail+fehlt" in url
    assert "fv_first_name=Max" in url
    assert "fv_organization_id=3" in url
    assert "ignored" not in url


def test_form_read_state():
    request = make_request(
        b"fe_email=Ungueltig&fv_email=max%40example.de&fv_role=admin&fv_extra=x"
    )

    field_errors, form_values = read_form_state(
        request,
        fields=["email", "role"],
    )

    assert field_errors == {"email": "Ungueltig"}
    assert form_values == {"email": "max@example.de", "role": "admin"}
