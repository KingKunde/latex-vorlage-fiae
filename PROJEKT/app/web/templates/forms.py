from urllib.parse import urlencode

from fastapi import Request

from app.services.errors import ValidationErrors

FIELD_ERROR_PREFIX = "fe_"
FIELD_VALUE_PREFIX = "fv_"


def build_form_redirect_url(
    path: str,
    *,
    validation_errors: ValidationErrors | None = None,
    values: dict[str, object] | None = None,
) -> str:
    query_params: dict[str, str] = {}

    if validation_errors is not None:
        first_error = validation_errors.first_error
        if first_error is not None:
            query_params["error"] = first_error
        for field_name, message in validation_errors.field_errors.items():
            query_params[f"{FIELD_ERROR_PREFIX}{field_name}"] = message

    if values is not None:
        for field_name, value in values.items():
            if value is None:
                continue
            query_params[f"{FIELD_VALUE_PREFIX}{field_name}"] = str(value)

    if not query_params:
        return path
    return f"{path}?{urlencode(query_params)}"


def read_form_state(
    request: Request, *, fields: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    field_errors = {
        field_name: value
        for field_name in fields
        if (
            value := request.query_params.get(f"{FIELD_ERROR_PREFIX}{field_name}")
        )
        is not None
    }
    form_values = {
        field_name: value
        for field_name in fields
        if (
            value := request.query_params.get(f"{FIELD_VALUE_PREFIX}{field_name}")
        )
        is not None
    }
    return field_errors, form_values
