class IntegrationError(Exception):
    code = "integration_error"
    retryable = False


class ProviderNotFoundError(IntegrationError):
    code = "provider_not_found"


class ProviderOperationNotSupported(IntegrationError):
    code = "operation_not_supported"


class ProviderTemporaryError(IntegrationError):
    code = "provider_temporary_error"
    retryable = True


class CredentialConfigurationError(IntegrationError):
    code = "credential_configuration_error"


class StorageValidationError(IntegrationError):
    code = "storage_validation_error"


class ImportParseError(IntegrationError):
    code = "import_parse_error"


class DuplicateImportError(IntegrationError):
    code = "duplicate_import"

    def __init__(self, existing_import_id: int) -> None:
        super().__init__(f"This file was already uploaded as import {existing_import_id}")
        self.existing_import_id = existing_import_id
