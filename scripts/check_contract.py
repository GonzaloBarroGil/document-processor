"""Compare the FastAPI app's generated OpenAPI against the hub contract.

Exit 0 when every contract path/method is implemented by the app; exit 1 otherwise.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import yaml

from document_processor.adapters.web.main import create_app
from document_processor.domain.services.api_key_service import ApiKeyService
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.dashboard_service import DashboardService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.quota_service import QuotaService
from document_processor.domain.services.review_service import ReviewService
from document_processor.domain.services.token_service import TokenService

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _load_contract(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _build_app_openapi() -> dict:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_documents = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    repo.update_parsed_data = AsyncMock()
    repo.list_review_queue = AsyncMock(return_value=([], 0))
    repo.count_by_status = AsyncMock(return_value={})

    storage = MagicMock()
    storage.store = AsyncMock()
    storage.retrieve = AsyncMock()

    document_service = DocumentService(
        repository=repo,
        storage=storage,
        ocr=MagicMock(),
        validator_registry={},
    )

    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(return_value=False)

    user_repo = MagicMock()
    user_repo.get_user_by_username = AsyncMock(return_value=None)
    user_repo.get_user_by_id = AsyncMock(return_value=None)
    refresh_repo = MagicMock()
    auth_service = AuthService(
        user_repository=user_repo,
        refresh_token_repository=refresh_repo,
        tokens=TokenService(),
        passwords=PasswordHasher(),
    )

    usage_repo = MagicMock()
    quota_service = QuotaService(usage_repository=usage_repo)

    app = create_app(
        document_service=document_service,
        api_key_repository=api_key_repo,
        validator_registry={},
        auth_service=auth_service,
        review_service=ReviewService(repository=repo),
        export_service=ExportService(repository=repo),
        quota_service=quota_service,
        api_key_service=ApiKeyService(repository=api_key_repo),
        dashboard_service=DashboardService(repository=repo),
    )
    return app.openapi()


def _path_methods(openapi: dict) -> set[tuple[str, str]]:
    operations: set[tuple[str, str]] = set()
    for path, item in openapi.get("paths", {}).items():
        for method, _ in item.items():
            if method in HTTP_METHODS:
                operations.add((path, method))
    return operations


def main() -> int:
    """Run the contract-vs-app comparison and return the process exit code."""
    contract_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/openapi.yaml"
    contract = _load_contract(contract_path)
    app_openapi = _build_app_openapi()

    contract_ops = _path_methods(contract)
    app_ops = _path_methods(app_openapi)

    missing = contract_ops - app_ops
    extra = app_ops - contract_ops

    if missing:
        print("ERROR: contract operations not implemented by the app:")
        for path, method in sorted(missing):
            print(f"  {method.upper()} {path}")
        return 1

    for path, method in sorted(extra):
        print(f"WARN: app operation not present in the contract: {method.upper()} {path}")

    print(f"OK: all {len(contract_ops)} contract operations implemented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
