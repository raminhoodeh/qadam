"""Structured subprocess receipts. Log text is not service-completion evidence."""

from datetime import datetime
from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def command_digest(command: tuple[str, ...] | list[str]) -> str:
    return sha256(json.dumps(list(command), separators=(",", ":")).encode()).hexdigest()


class CommandReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal["qadam-command-receipt.1"] = "qadam-command-receipt.1"
    run_id: str = Field(min_length=1)
    command_digest: str = Field(min_length=64, max_length=64)
    started_at: str
    completed_at: str
    returncode: int
    state: Literal["completed", "failed"]
    work_result: dict = Field(default_factory=dict)

    @field_validator("started_at", "completed_at")
    @classmethod
    def aware(cls, value):
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("receipt_timezone_required")
        return value

    @model_validator(mode="after")
    def coherent(self):
        if datetime.fromisoformat(self.completed_at) < datetime.fromisoformat(self.started_at):
            raise ValueError("receipt_time_reversed")
        if (self.returncode == 0) != (self.state == "completed"):
            raise ValueError("receipt_exit_state_mismatch")
        if self.work_result:
            count = self.work_result.get("validation_error_count")
            if type(count) is not int or count < 0:
                raise ValueError("invalid_work_validation_count")
            if "material_change_detected" in self.work_result and type(self.work_result["material_change_detected"]) is not bool:
                raise ValueError("invalid_material_change_type")
            if count and self.returncode == 0:
                raise ValueError("script_success_with_failed_work_validation")
        return self


def validate_command_receipt(payload: dict, *, run_id: str, command: tuple[str, ...], returncode: int) -> CommandReceipt:
    receipt = CommandReceipt.model_validate(payload)
    if receipt.run_id != run_id or receipt.command_digest != command_digest(command) or receipt.returncode != returncode:
        raise ValueError("command_receipt_binding_mismatch")
    return receipt
