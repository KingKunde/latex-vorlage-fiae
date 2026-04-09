from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationErrors:
    field_errors: dict[str, str] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return bool(self.field_errors)

    @property
    def first_error(self) -> str | None:
        return next(iter(self.field_errors.values()), None)


def single_error(field_name: str, message: str) -> ValidationErrors:
    return ValidationErrors({field_name: message})
