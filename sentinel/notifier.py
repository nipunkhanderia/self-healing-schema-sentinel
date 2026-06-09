"""
Notifier — attaches drift report to Allure and posts GitHub PR comment.

Call notify() at the end of a healing run to record what happened.
"""
import json
from sentinel.models import DriftReport, HealResult
from sentinel.config import settings


class DriftNotifier:

    def notify(self, heal_result: HealResult) -> None:
        """Post notifications for a completed heal run."""
        self._attach_allure(heal_result)
        if settings.output_mode == "pr" and heal_result.pr_url:
            self._post_pr_comment(heal_result)

    def _attach_allure(self, heal_result: HealResult) -> None:
        """
        Write an Allure-compatible attachment file.
        When pytest is run with --alluredir, Allure picks this up automatically.
        The attachment is a JSON summary of the drift report.
        """
        try:
            import allure
            report = heal_result.drift_report
            attachment_data = {
                "schema_name": report.schema_name,
                "baseline_version": report.baseline_version,
                "detected_at": report.detected_at.isoformat(),
                "summary": report.summary,
                "drifts": [d.model_dump() for d in report.drifts],
                "generated_test_path": heal_result.output_path,
                "pr_url": heal_result.pr_url,
            }
            allure.attach(
                body=json.dumps(attachment_data, indent=2),
                name=f"Schema Drift Report — {report.schema_name}",
                attachment_type=allure.attachment_type.JSON,
            )
        except ImportError:
            # Allure not available — write to file instead
            import os
            os.makedirs(".sentinel/reports", exist_ok=True)
            path = f".sentinel/reports/drift_{heal_result.drift_report.schema_name}.json"
            with open(path, "w") as f:
                json.dump(heal_result.drift_report.model_dump(mode="json"), f, indent=2, default=str)

    def _post_pr_comment(self, heal_result: HealResult) -> None:
        """Post a summary comment on the opened PR."""
        if not settings.github_token or not heal_result.pr_url:
            return
        try:
            from github import Github
            gh = Github(settings.github_token)
            repo = gh.get_repo(settings.github_repo)
            pr_number = int(heal_result.pr_url.rstrip("/").split("/")[-1])
            pr = repo.get_pull(pr_number)
            report = heal_result.drift_report
            comment_lines = [
                f"### schema-sentinel drift summary",
                f"",
                f"| Field | Change | Severity |",
                f"|---|---|---|",
            ]
            for d in report.drifts:
                comment_lines.append(
                    f"| `{d.field_path}` | {d.drift_type.value} | {d.severity} |"
                )
            comment_lines += [
                f"",
                f"Tests auto-generated and committed to this branch. Please review before merging.",
            ]
            pr.create_issue_comment("\n".join(comment_lines))
        except Exception as e:
            print(f"Warning: could not post PR comment: {e}")
