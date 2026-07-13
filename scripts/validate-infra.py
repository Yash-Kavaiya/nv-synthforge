"""Validate repository-owned YAML and cross-file infrastructure contracts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_FILES = (
    ROOT / "docker-compose.yml",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / "cloudbuild.frontend.yaml",
)


class ValidationError(RuntimeError):
    """Raised when an infrastructure contract is inconsistent."""


def load_yaml(path: Path) -> Any:
    try:
        # BaseLoader follows GitHub Actions' treatment of the `on` key instead of
        # YAML 1.1's surprising boolean coercion.
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise ValidationError(f"cannot parse {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{path.relative_to(ROOT)} must contain a mapping at its root")
    print(f"OK YAML: {path.relative_to(ROOT).as_posix()}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_compose(compose: dict[str, Any]) -> None:
    services = compose.get("services")
    require(isinstance(services, dict), "docker-compose.yml must define services")

    expected_builds = {
        "backend": ("./backend", ROOT / "backend" / "Dockerfile"),
        "frontend": ("./frontend", ROOT / "frontend" / "Dockerfile"),
    }
    for service_name, (context, dockerfile_path) in expected_builds.items():
        service = services.get(service_name)
        require(isinstance(service, dict), f"Compose service {service_name!r} is missing")
        build = service.get("build")
        require(isinstance(build, dict), f"Compose service {service_name!r} needs a build mapping")
        require(build.get("context") == context, f"Compose {service_name} context must be {context}")
        require(build.get("dockerfile") == "Dockerfile", f"Compose {service_name} must explicitly reference Dockerfile")
        require(dockerfile_path.is_file(), f"referenced file is missing: {dockerfile_path.relative_to(ROOT).as_posix()}")

    frontend = services["frontend"]
    build_args = frontend["build"].get("args", {})
    environment = frontend.get("environment", {})
    require("NEXT_PUBLIC_API_URL" in build_args, "frontend build args must include NEXT_PUBLIC_API_URL")
    require("NEXT_PUBLIC_API_URL" in environment, "frontend environment must include NEXT_PUBLIC_API_URL")
    print("OK Compose contract: backend/frontend Dockerfiles and NEXT_PUBLIC_API_URL")


def validate_ci(workflow: dict[str, Any]) -> None:
    require("on" in workflow, ".github/workflows/ci.yml must define triggers")
    jobs = workflow.get("jobs")
    require(isinstance(jobs, dict), ".github/workflows/ci.yml must define jobs")
    require({"backend-tests", "frontend-quality", "infrastructure"}.issubset(jobs), "CI jobs are incomplete")

    workflow_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    required_commands = (
        "uv sync --locked",
        "uv run pytest -q",
        "pnpm install --frozen-lockfile",
        "pnpm lint",
        "pnpm build",
    )
    for command in required_commands:
        require(command in workflow_text, f"CI is missing command: {command}")
    print("OK CI contract: locked uv/pnpm install, test, lint, and build commands")


def validate_cloud_build(config: dict[str, Any]) -> None:
    require(isinstance(config.get("steps"), list), "cloudbuild.frontend.yaml must define build steps")
    require(config.get("images") == ["${_IMAGE}"], "Cloud Build must publish ${_IMAGE}")
    text = (ROOT / "cloudbuild.frontend.yaml").read_text(encoding="utf-8")
    require("NEXT_PUBLIC_API_URL=${_NEXT_PUBLIC_API_URL}" in text, "Cloud Build must forward NEXT_PUBLIC_API_URL")
    print("OK Cloud Build contract: frontend API URL build argument and image output")


def validate_environment_names() -> None:
    checked_files = [
        ROOT / ".env.example",
        ROOT / "README.md",
        ROOT / "docker-compose.yml",
        *sorted((ROOT / "docs").glob("*.md")),
    ]
    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        require("NEXT_PUBLIC_API_BASE_URL" not in text, f"stale NEXT_PUBLIC_API_BASE_URL in {path.relative_to(ROOT)}")
    require("NEXT_PUBLIC_API_URL=" in (ROOT / ".env.example").read_text(encoding="utf-8"), ".env.example must define NEXT_PUBLIC_API_URL")
    print("OK environment contract: NEXT_PUBLIC_API_URL is consistent")


def validate_api_docs() -> None:
    api_client = (ROOT / "frontend" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    api_docs = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    routes = (
        "/api/v1/health",
        "/api/v1/domains",
        "/api/v1/gallery",
        "/api/v1/generate",
        "/api/v1/jobs/",
        "/api/v1/benchmarks",
    )
    for route in routes:
        require(route in api_client, f"frontend API client no longer references documented route {route}")
        require(route in api_docs, f"docs/API.md is missing frontend route {route}")
    print("OK API documentation contract: frontend routes are documented")


def validate_local_markdown_links() -> None:
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    markdown_files = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        *sorted((ROOT / "docs").glob("*.md")),
    ]
    checked = 0
    for path in markdown_files:
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            require((path.parent / target).resolve().exists(), f"broken local link in {path.relative_to(ROOT)}: {target}")
            checked += 1
    print(f"OK documentation links: {checked} local targets")


def main() -> int:
    loaded = {path: load_yaml(path) for path in YAML_FILES}
    validate_compose(loaded[ROOT / "docker-compose.yml"])
    validate_ci(loaded[ROOT / ".github" / "workflows" / "ci.yml"])
    validate_cloud_build(loaded[ROOT / "cloudbuild.frontend.yaml"])
    validate_environment_names()
    validate_api_docs()
    validate_local_markdown_links()
    print("Infrastructure validation passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc
