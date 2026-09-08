import json
import logging

from app.config import get_settings
from app.llm.client import get_llm
from app.logging_utils import log_operation
from app.models.schemas import ResourceRequest, ToolResult

logger = logging.getLogger(__name__)

ALIASES = {
    "generative ai": "genai", "genai": "genai", "python": "python", "cloud": "cloud",
    "data engineering": "data_engineering", "machine learning": "machine_learning",
}


class LearningResourceTool:
    name = "learning_resource"

    def run(self, topic: str, question: str | None = None) -> ToolResult:
        key = next((value for alias, value in ALIASES.items() if alias in topic.lower()), None)
        if not key:
            available = ", ".join(sorted({item.title() for item in ALIASES}))
            return ToolResult(
                tool_name=self.name,
                answer=f"I have structured learning roadmaps for: {available}. Which one would you like?",
            )

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
        if request.section in {"summary", "full_resource"}:
            selected_data = {**data, "requested_section": request.section}
        else:
            selected_data = {
                "title": data["title"], "requested_section": request.section,
                request.section: data[request.section],
            }
        selected_data["source_type"] = "curated_learning_resource"
        selected_data["source_file"] = path.name
        return ToolResult(tool_name=self.name, answer=answer, data=selected_data)

    def _identify_section(self, question: str) -> ResourceRequest:
        text = question.lower()
        if any(detail_word in text for detail_word in ("complete", "full", "detailed")) and any(
            roadmap_word in text for roadmap_word in ("roadmap", "learning path", "study plan")
        ):
            logger.info("resource_section_selected method=deterministic section=full_resource")
            return ResourceRequest(section="full_resource", confidence=1)
        deterministic = (
            ("prerequisites", ("prerequisite", "requirements before")),
            ("projects", ("project", "portfolio")),
            ("next_steps", ("next step", "what next")),
            ("recommended_topics", ("recommended topic", "topics should")),
            ("learning_stages", ("learning stage", "stages", "phases")),
            ("summary", (
                "i want to learn", "want to learn", "how should i learn", "how do i learn",
                "start learning", "get started", "what do i need", "what it needs",
                "roadmap", "learning path", "study plan",
            )),
        )
        for section, phrases in deterministic:
            if any(phrase in text for phrase in phrases):
                logger.info("resource_section_selected method=deterministic section=%s", section)
                return ResourceRequest(section=section, confidence=1)

        instruction = """Classify which part of a learning roadmap the user requests.
Use prerequisites for knowledge needed before starting; learning_stages for sequence/phases;
recommended_topics for subjects to study; projects for practice ideas; next_steps for what to do
afterward; summary for a broad helpful overview; and full_resource only when the complete detailed
roadmap is explicitly requested. Return low confidence if the request is unclear."""
        with log_operation(logger, "resource_section_classification"):
            try:
                result = get_llm().with_structured_output(ResourceRequest).invoke(
                    [("system", instruction), ("human", question)]
                )
                logger.info(
                    "resource_section_selected method=qwen3 section=%s confidence=%.2f",
                    result.section, result.confidence,
                )
                return result
            except Exception:
                logger.exception("Resource section classification failed")
                return ResourceRequest(section="full_resource", confidence=0)

    @staticmethod
    def _format_section(data: dict, section: str) -> str:
        title = data["title"]
        if section == "prerequisites":
            return f"Yes. The {title} has these prerequisites:\n- " + "\n- ".join(data["prerequisites"])
        if section == "projects":
            return f"Recommended projects for the {title}:\n- " + "\n- ".join(data["projects"])
        if section == "next_steps":
            return f"Next steps after the {title}:\n- " + "\n- ".join(data["next_steps"])
        if section == "recommended_topics":
            return f"Recommended topics for the {title}:\n- " + "\n- ".join(data["recommended_topics"])
        if section == "learning_stages":
            lines = [f"Learning stages for the {title}:"]
            for stage in data["learning_stages"]:
                lines.extend(["", stage["name"], *[f"- {topic}" for topic in stage["topics"]]])
            return "\n".join(lines)
        if section == "summary":
            return LearningResourceTool._format_summary(data)
        return LearningResourceTool._format_full_resource(data)

    @staticmethod
    def _format_summary(data: dict) -> str:
        lines = [
            data["title"], data["description"], "", "What you need before starting",
            *[f"- {item}" for item in data["prerequisites"]], "", "Learning path",
        ]
        for stage in data["learning_stages"]:
            lines.append(f"- {stage['name']}: " + ", ".join(stage["topics"]))
        lines.extend([
            "", "Practice projects", *[f"- {item}" for item in data["projects"][:3]],
            "", "Recommended next step", f"- {data['next_steps'][0]}", "",
            "You can ask me for the prerequisites, stages, topics, projects, next steps, or the complete roadmap.",
        ])
        return "\n".join(lines)

    @staticmethod
    def _format_full_resource(data: dict) -> str:
        lines = [
            data["title"], data["description"], "", "Prerequisites",
            *[f"- {item}" for item in data["prerequisites"]],
        ]
        for stage in data["learning_stages"]:
            lines.extend(["", stage["name"], *[f"- {item}" for item in stage["topics"]]])
        lines.extend([
            "", "Recommended topics", *[f"- {item}" for item in data["recommended_topics"]],
            "", "Projects:", *[f"- {item}" for item in data["projects"]],
            "", "Next steps", *[f"- {item}" for item in data["next_steps"]],
        ])
        return "\n".join(lines)
