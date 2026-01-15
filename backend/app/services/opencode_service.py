import ipaddress
import json
import os
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

from .file_manager import get_project_path


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_SKILL_FILENAMES = ("SKILL.md", "skill.md")


class OpenCodeService:
    def __init__(self) -> None:
        self.base_url = os.getenv("OPENCODE_BASE_URL", "http://127.0.0.1:4096").rstrip("/")
        self.agent = os.getenv("OPENCODE_AGENT", "build")
        self.provider_id = os.getenv("OPENCODE_PROVIDER_ID")
        self.model_id = os.getenv("OPENCODE_MODEL_ID")
        self.timeout = float(os.getenv("OPENCODE_TIMEOUT", "120"))
        self.system_prompt_path = os.getenv("OPENCODE_SYSTEM_PROMPT_PATH", "opencode/system_prompt.txt")
        self.agents_template_path = os.getenv("OPENCODE_AGENTS_TEMPLATE_PATH", "opencode/AGENTS.md")
        self.skill_path = os.getenv("OPENCODE_SKILL_PATH", "").strip()
        self.skill_filenames = [
            name.strip()
            for name in os.getenv("OPENCODE_SKILL_FILENAMES", ",".join(DEFAULT_SKILL_FILENAMES)).split(",")
            if name.strip()
        ]
        self.permission_pattern = os.getenv("OPENCODE_PERMISSION_PATTERN", "*")
        self.permission_list = os.getenv(
            "OPENCODE_PERMISSIONS",
            "bash,edit,webfetch,external_directory",
        )
        self.session_map: Dict[str, str] = {}
        self.session = requests.Session()
        self.session.trust_env = not self._should_bypass_proxy()

    def _should_bypass_proxy(self) -> bool:
        override = os.getenv("OPENCODE_IGNORE_PROXY", "").strip().lower()
        if override in {"1", "true", "yes", "y"}:
            return True
        hostname = urlparse(self.base_url).hostname
        if not hostname:
            return False
        if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return True
        try:
            return ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            return False

    def _project_directory(self, project_id: Optional[str]) -> str:
        if project_id:
            return get_project_path(project_id)
        return BASE_DIR

    def _load_file(self, path: str) -> str:
        if not path:
            return ""
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        return self._load_file_absolute(path)

    def _load_file_absolute(self, path: str) -> str:
        if not path or not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()

    def _ensure_agents_file(self, project_id: Optional[str]) -> None:
        if not project_id:
            return
        project_dir = self._project_directory(project_id)
        target_path = os.path.join(project_dir, "AGENTS.md")
        if os.path.exists(target_path):
            return
        template = self._load_file(self.agents_template_path)
        if not template:
            return
        os.makedirs(project_dir, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as handle:
            handle.write(template)

    def _find_skill_file(self, project_dir: str) -> str:
        if self.skill_path:
            candidate = self.skill_path
            if not os.path.isabs(candidate):
                candidate_project = os.path.join(project_dir, candidate)
                if os.path.exists(candidate_project):
                    return candidate_project
                candidate = os.path.join(BASE_DIR, candidate)
            if os.path.exists(candidate):
                return candidate

        for filename in self.skill_filenames:
            candidate = os.path.join(project_dir, filename)
            if os.path.exists(candidate):
                return candidate

        return ""

    def _load_skill_content(self, project_dir: str) -> str:
        skill_path = self._find_skill_file(project_dir)
        if not skill_path:
            return ""
        return self._load_file_absolute(skill_path)

    def _build_system_prompt(self, message: str, tool_context: Optional[dict], project_dir: str) -> str:
        parts = []
        system_prompt = self._load_file(self.system_prompt_path)
        if system_prompt:
            parts.append(system_prompt)

        skill_content = self._load_skill_content(project_dir)
        if skill_content:
            parts.append("Skill instructions:\n" + skill_content)

        if tool_context:
            parts.append(
                "\n".join(
                    [
                        "Current tool context:",
                        f"- Tool name: {tool_context.get('tool_name', 'unknown')}",
                        f"- Description: {tool_context.get('description', 'N/A')}",
                        f"- Parameters: {tool_context.get('parameters', [])}",
                        f"- Current values: {tool_context.get('current_values', {})}",
                    ]
                )
            )

        return "\n\n".join([p for p in parts if p])

    def _permission_rules(self) -> list:
        permissions = [p.strip() for p in self.permission_list.split(",") if p.strip()]
        return [
            {"permission": permission, "pattern": self.permission_pattern, "action": "allow"}
            for permission in permissions
        ]

    def _request(self, method: str, path: str, project_dir: str, json_body: Optional[dict] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        return self.session.request(
            method,
            url,
            params={"directory": project_dir},
            json=json_body,
            timeout=self.timeout,
        )

    def _create_session(self, project_dir: str) -> str:
        payload = {"permission": self._permission_rules()}
        response = self._request("POST", "/session", project_dir, json_body=payload)
        response.raise_for_status()
        data = response.json()
        session_id = data.get("id")
        if not session_id:
            raise RuntimeError("OpenCode session creation failed: missing session id")
        return session_id

    def get_or_create_session(self, app_session_id: str, project_id: Optional[str]) -> str:
        key = f"{project_id or 'global'}::{app_session_id}"
        if key in self.session_map:
            return self.session_map[key]
        project_dir = self._project_directory(project_id)
        session_id = self._create_session(project_dir)
        self.session_map[key] = session_id
        return session_id

    def _extract_text(self, payload: dict) -> str:
        parts = payload.get("parts", [])
        text_parts = [part.get("text", "") for part in parts if part.get("type") == "text"]
        if text_parts:
            return "".join(text_parts).strip()
        info = payload.get("info", {})
        if isinstance(info, dict):
            error = info.get("error")
            if isinstance(error, dict):
                name = error.get("name", "OpenCodeError")
                data = error.get("data") if isinstance(error.get("data"), dict) else {}
                message = ""
                if data:
                    message = data.get("message") or data.get("responseBody") or ""
                if message:
                    return f"[OpenCode] {name}: {message}".strip()
        if parts:
            part_types = sorted({part.get("type", "unknown") for part in parts})
            return f"[OpenCode] Response contained no text parts (types: {', '.join(part_types)})."
        return ""

    def _parse_json(self, text: str) -> dict:
        if not text:
            raise ValueError("Empty response from OpenCode")

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("OpenCode response did not contain JSON")

        return json.loads(text[start : end + 1])

    def send_message(
        self,
        message: str,
        project_id: Optional[str],
        app_session_id: str,
        tool_context: Optional[dict] = None,
    ) -> str:
        self._ensure_agents_file(project_id)
        project_dir = self._project_directory(project_id)
        session_id = self.get_or_create_session(app_session_id, project_id)

        payload = {
            "parts": [
                {
                    "type": "text",
                    "text": message,
                }
            ]
        }

        system_prompt = self._build_system_prompt(message, tool_context, project_dir)
        if system_prompt:
            payload["system"] = system_prompt

        if self.agent:
            payload["agent"] = self.agent

        if self.provider_id and self.model_id:
            payload["model"] = {"providerID": self.provider_id, "modelID": self.model_id}

        response = self._request("POST", f"/session/{session_id}/message", project_dir, json_body=payload)
        response.raise_for_status()
        data = response.json()
        return self._extract_text(data)

    def request_json(
        self,
        message: str,
        project_id: Optional[str],
        app_session_id: str,
        tool_context: Optional[dict] = None,
    ) -> dict:
        text = self.send_message(message, project_id, app_session_id, tool_context)
        return self._parse_json(text)


opencode_service = OpenCodeService()
