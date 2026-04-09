from types import SimpleNamespace

from app.services.errors import single_error
from app.web.templates.forms import build_form_redirect_url, read_form_state


def test_build_form_redirect_url_keeps_errors_and_values():
    redirect_url = build_form_redirect_url(
        "/users/page",
        validation_errors=single_error("email", "E-Mail-Adresse ist ungültig."),
        values={"email": "foo", "role": "admin"},
    )

    assert redirect_url.startswith("/users/page?")
    assert "error=E-Mail-Adresse+ist+ung%C3%BCltig." in redirect_url
    assert "fe_email=E-Mail-Adresse+ist+ung%C3%BCltig." in redirect_url
    assert "fv_email=foo" in redirect_url
    assert "fv_role=admin" in redirect_url


def test_read_form_state_filters_requested_fields():
    request = SimpleNamespace(
        query_params={
            "fe_email": "E-Mail-Adresse ist ungültig.",
            "fv_email": "foo@example.de",
        }
    )

    field_errors, form_values = read_form_state(
        request,
        fields=["email", "role"],
    )

    assert field_errors == {"email": "E-Mail-Adresse ist ungültig."}
    assert form_values == {"email": "foo@example.de"}
