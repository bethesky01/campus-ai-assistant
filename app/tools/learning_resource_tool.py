import json
import logging
from pathlib import Path

from app.config import get_settings
from app.llm.client import get_llm
from app.logging_utils import log_operation
from app.models.schemas import ResourceRequest, ToolResult

logger = logging.getLogger(__name__)

ALIASES = {"generative ai": "genai", "genai": "genai", "python": "python", "cloud": "cloud", "data engineering": "data_engineering", "machine learning": "machine_learning"}


class LearningResourceTool:
    name = "learning_resource"

    def run(self, topic: str, question: str | None = None) -> ToolResult:
        key = next((value for alias, value in ALIASES.items() if alias in topic.lower()), None)
        if not key:
            available = ", ".join(sorted({x.title() for x in ALIASES}))
            return ToolResult(tool_name=self.name, answer=f"I have structured learning roadmaps for: {available}. Which one would you like?")
        path = get_settings().learning_resources_dir / f"{key}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        request = self._identify_section(question) if question else ResourceRequest(section="full_resource", confidence=1)
        if request.confidence < get_settings().router_confidence_threshold:
            return ToolResult(
                tool_name=self.name,
                answer="Would you like the prerequisites, learning stages, recommended topics, projects, next steps, or the complete roadmap?",
                data={"title": data["title"], "requested_section": "clarification"},
            )
        answer = self._format_section(data, request.section)
        selected_data = data if request.section == "full_resource" else {
            "title": data["title"], "requested_section": request.section, request.section: data[request.section],
        }
        return ToolResult(tool_name=self.name, answer=answer, data=selected_data)

    def _identify_section(self, question: str) -> ResourceRequest:
        text = question.lower()
        deterministic = (
            ("prerequisites", ("prerequisite", "requirements before")),
            ("projects", ("project", "portfolio")),
            ("next_steps", ("next step", "what next")),
            ("recommended_topics", ("recommended topic", "topics should")),
            ("learning_stages", ("learning stage", "stages", "phases")),
            ("full_resource", ("roadmap", "learning path", "study plan", "how should i learn", "how do i learn")),
        )
        for section, phrases in deterministic:
            if any(phrase in text for phrase in phrases):
                logger.info("resource_section_selected method=deterministic section=%s", section)
                return ResourceRequest(section=section, confidence=1)

        instruction = """Classify which part of a learning roadmap the user requests.
Use prerequisites for knowledge needed before starting; learning_stages for sequence/phases;
recommended_topics for subjects to study; projects for practice ideas; next_steps for what to do
afterward; full_resource for a broad roadmap. Return low confidence if the request is unclear."""
        with log_operation(logger, "resource_section_classification"):
            try:
                result = get_llm().with_structured_output(ResourceRequest).invoke(
                    [("system", instruction), ("human", question)]
                )
                logger.info("resource_section_selected method=qwen3 section=%s confidence=%.2f", result.section, result.confidence)
                return result
            except Exception:
                logger.exception("Resource section classification failed")
                return ResourceRequest(section="full_resource", confidence=0)

    @staticmethod
    def _format_section(data: dict, section: str) -> str:
        title = data["title"]
        if section == "prerequisites":
            return f"Yes. The {title} lists these prerequisites: " + ", ".join(data["prerequisites"]) + "."
        if section == "projects":
            return f"Recommended projects for the {title}:\n • " + "\n • ".join(data["projects"])
        if section == "next_steps":
            return f"Next steps after the {title}:\n • " + "\n • ".join(data["next_steps"])
        if section == "recommended_topics":
            return f"Recommended topics for the {title}:\n • " + "\n • ".join(data["recommended_topics"])
        if section == "learning_stages":
            lines = [f"Learning stages for the {title}:"]
            for stage in data["learning_stages"]:
                lines.append(f"\n{stage['name']}\n • " + "\n • ".join(stage["topics"]))
            return "\n".join(lines)
        return LearningResourceTool._format_full_resource(data)

    @staticmethod
    def _format_full_resource(data: dict) -> str:
        lines = [data["title"], data["description"], "", "Prerequisites: " + ", ".join(data["prerequisites"])]
        for stage in data["learning_stages"]:
            lines.extend(["", stage["name"], " • " + "\n • ".join(stage["topics"])])
        lines.extend(["", "Projects: " + "; ".join(data["projects"]), "Next steps: " + "; ".join(data["next_steps"])])
        return "\n".join(lines)
