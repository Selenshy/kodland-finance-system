from pydantic import BaseModel


class ImportMappingTemplateOut(BaseModel):
    id: int
    legal_entity_id: int | None
    name: str
    target_kind: str
    column_mapping: dict

    model_config = {"from_attributes": True}


class ImportMappingTemplateCreate(BaseModel):
    legal_entity_id: int | None = None
    name: str
    target_kind: str = "journal_entries"
    column_mapping: dict


class ImportUploadResult(BaseModel):
    upload_token: str
    columns: list[str]
    preview_rows: list[dict]
    total_rows: int


class ImportValidateRequest(BaseModel):
    upload_token: str
    legal_entity_id: int
    column_mapping: dict
    mapping_template_id: int | None = None


class ImportRowError(BaseModel):
    row_number: int
    message: str


class ImportValidateResult(BaseModel):
    valid_rows: int
    invalid_rows: int
    errors: list[ImportRowError]
    can_commit: bool


class ImportCommitRequest(BaseModel):
    upload_token: str
    legal_entity_id: int
    column_mapping: dict
    file_name: str
    mapping_template_id: int | None = None


class ImportCommitResult(BaseModel):
    import_batch_id: int
    entries_created: int
    lines_created: int
    error_count: int
    errors: list[ImportRowError]
