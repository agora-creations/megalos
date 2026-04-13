"""MCP tool functions for mikros workflow engine."""

import json

import jsonschema

from server import state
from server.state import COMPLETE as _COMPLETE

_DEFAULT_MAX_RETRIES = 3

_DO_NOT_RULES = [
    "Do NOT skip ahead to later steps.",
    "Do NOT produce final artifacts yet.",
    "Do NOT ask multiple questions at once.",
    "Do NOT proceed until all gates for this step are satisfied.",
    "Do NOT submit a step without showing your work to the user and waiting for their confirmation. Each step is a conversation, not a task you complete silently.",
    "Do NOT submit multiple steps in a single response. Complete ONE step, present it, wait for the user to respond, then move to the next.",
    "Do NOT reveal step names, step numbers, or internal workflow mechanics to the user. The workflow should feel like a natural conversation, not a numbered checklist. Never say things like 'Step 2: Decompose and Structure' or 'we are now in the plan phase'.",
]


def _find_step(workflow, step_id):
    """Find (index, step_dict) in a workflow by id. Returns (-1, None) if missing."""
    for i, step in enumerate(workflow["steps"]):
        if step["id"] == step_id:
            return i, step
    return -1, None


def _resolve_session(session_id, workflows):
    """Look up session and its workflow. Returns (session, wf) or (None, error_dict)."""
    try:
        session = state.get_session(session_id)
    except KeyError as e:
        return None, {"error": str(e), "session_id": session_id}
    wf = workflows.get(session["workflow_type"])
    if not wf:
        return None, {"error": f"Workflow '{session['workflow_type']}' not loaded", "session_id": session_id}
    return (session, wf), None


def _validate_output(content: str, step: dict) -> list[str] | None:
    """Validate content against step's output_schema. Returns error list or None if valid/no schema."""
    output_schema = step.get("output_schema")
    if not output_schema:
        return None
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        return [f"Content is not valid JSON: {e}"]
    validator = jsonschema.Draft202012Validator(output_schema)
    errors = [err.message for err in validator.iter_errors(parsed)]
    return errors if errors else None


_SUMMARY_LIMIT = 500


def _assemble_context(inject_context: list[dict], step_data: dict) -> list[dict]:
    """Build injected context from inject_context spec and stored step_data."""
    result = []
    for entry in inject_context:
        source_id = entry["from"]
        raw = step_data.get(source_id)
        if raw is None:
            result.append({"from": source_id, "content": None})
            continue

        # Try to parse as JSON for field filtering
        parsed = None
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass

        fields = entry.get("fields")
        if fields and isinstance(parsed, dict):
            content = {k: parsed.get(k) for k in fields}
            item = {"from": source_id, "fields": content}
        else:
            content = raw
            if entry.get("summary") and len(content) > _SUMMARY_LIMIT:
                content = content[:_SUMMARY_LIMIT] + "[truncated]"
            item = {"from": source_id, "content": content}

        result.append(item)
    return result


def register_tools(mcp, workflows):
    """Register workflow tools on the FastMCP app."""

    @mcp.tool()
    def list_workflows(category: str = "") -> dict:
        """List available workflow types, optionally filtered by category.

        Categories: writing_communication, analysis_decision, planning_strategy,
        learning_development, professional, creative.
        Pass empty string or omit to list all.
        """
        items = []
        for name, wf in workflows.items():
            wf_cat = wf.get("category", "")
            if category and wf_cat != category:
                continue
            items.append({
                "name": name,
                "description": wf.get("description", ""),
                "category": wf_cat,
                "steps": len(wf["steps"]),
            })
        return {"workflows": items, "total": len(items)}

    @mcp.tool()
    def start_workflow(workflow_type: str, context: str) -> dict:
        """Start a new workflow session. Returns the first step's directive."""
        if workflow_type not in workflows:
            return {
                "error": f"Unknown workflow type: {workflow_type}",
                "available_types": list(workflows.keys()),
            }

        active = state.count_active()
        if active >= 5:
            active_sessions = [s for s in state.list_sessions() if s["status"] == "active"]
            return {"error": f"Session cap reached ({active}/5). Delete or complete a session first.", "active_sessions": active_sessions}

        wf = workflows[workflow_type]
        first_step = wf["steps"][0]
        sid = state.create_session(workflow_type, current_step=first_step["id"])

        result = {
            "session_id": sid,
            "workflow_type": workflow_type,
            "current_step": {"id": first_step["id"], "title": first_step["title"]},
            "directive": first_step["directive_template"],
            "do_not": _DO_NOT_RULES,
            "gates": first_step["gates"],
            "context": context,
        }
        if first_step.get("directives"):
            result["directives"] = first_step["directives"]
        return result

    @mcp.tool()
    def get_state(session_id: str) -> dict:
        """Get current session state: step, progress, and what's pending."""
        resolved, err = _resolve_session(session_id, workflows)
        if err:
            return err
        session, wf = resolved

        steps = wf["steps"]
        idx, current = _find_step(wf, session["current_step"])
        pending = [s["title"] for s in steps[idx + 1:]] if idx >= 0 else []

        result = {
            "session_id": session_id,
            "workflow_type": session["workflow_type"],
            "current_step": {"id": current["id"], "title": current["title"]} if current else None,
            "progress": f"step {idx + 1} of {len(steps)}" if idx >= 0 else "unknown",
            "pending_steps": pending,
            "step_data": session["step_data"],
        }
        if current and current.get("inject_context"):
            result["injected_context"] = _assemble_context(current["inject_context"], session["step_data"])
        if current and current.get("directives"):
            result["directives"] = current["directives"]
        return result

    @mcp.tool()
    def get_guidelines(session_id: str) -> dict:
        """Get anti-patterns and gates for the current step."""
        resolved, err = _resolve_session(session_id, workflows)
        if err:
            return err
        session, wf = resolved

        _, step = _find_step(wf, session["current_step"])
        if not step:
            return {"error": f"Step '{session['current_step']}' not found in workflow", "session_id": session_id}

        return {
            "session_id": session_id,
            "current_step": {"id": step["id"], "title": step["title"]},
            "anti_patterns": step["anti_patterns"],
            "gates": step["gates"],
        }

    @mcp.tool()
    def submit_step(session_id: str, step_id: str, content: str) -> dict:
        """Submit content for the current step. Enforces ordering — no skips, no backwards."""
        resolved, err = _resolve_session(session_id, workflows)
        if err:
            return err
        session, wf = resolved

        current = session["current_step"]
        if current == _COMPLETE:
            return {
                "error": "Workflow already complete. Call generate_artifact to get final output.",
                "session_id": session_id,
            }

        if step_id != current:
            return {
                "error": f"Out-of-order submission: expected '{current}', got '{step_id}'",
                "session_id": session_id,
                "expected_step": current,
                "submitted_step": step_id,
            }

        steps = wf["steps"]
        idx, step = _find_step(wf, step_id)

        # Validate against output_schema if present
        validation_errors = _validate_output(content, step)
        if validation_errors is not None:
            max_retries = step.get("max_retries", _DEFAULT_MAX_RETRIES)
            retry_count = state.increment_retry(session_id, step_id)
            if retry_count >= max_retries:
                return {
                    "status": "validation_error",
                    "errors": validation_errors,
                    "session_id": session_id,
                    "step_id": step_id,
                    "retries_exhausted": True,
                    "message": f"Max retries ({max_retries}) exceeded. Workflow stalled.",
                }
            err_result: dict = {
                "status": "validation_error",
                "errors": validation_errors,
                "session_id": session_id,
                "step_id": step_id,
                "retries_remaining": max_retries - retry_count,
            }
            hint = step.get("validation_hint")
            if hint:
                err_result["validation_hint"] = hint
            return err_result

        step_data = session["step_data"]
        step_data[step_id] = content

        is_last = idx == len(steps) - 1
        next_step_id = _COMPLETE if is_last else steps[idx + 1]["id"]
        state.update_session(session_id, current_step=next_step_id, step_data=step_data)

        result: dict = {
            "session_id": session_id,
            "submitted": {"id": step["id"], "title": step["title"]},
            "progress": f"step {idx + 1} of {len(steps)} complete",
        }

        if is_last:
            result["status"] = "workflow_complete"
            result["message"] = "All steps complete. Call generate_artifact to produce final output."
        else:
            nxt = steps[idx + 1]
            result["next_step"] = {"id": nxt["id"], "title": nxt["title"]}
            result["directive"] = nxt["directive_template"]
            result["do_not"] = _DO_NOT_RULES
            result["gates"] = nxt["gates"]
            if nxt.get("inject_context"):
                result["injected_context"] = _assemble_context(nxt["inject_context"], step_data)
            if nxt.get("directives"):
                result["directives"] = nxt["directives"]

        return result

    @mcp.tool()
    def revise_step(session_id: str, step_id: str) -> dict:
        """Revise a previously completed step. Resets current_step to the target,
        returns its previous content, and deletes all step_data after it."""
        resolved, err = _resolve_session(session_id, workflows)
        if err:
            return err
        session, wf = resolved

        target_idx, target_step = _find_step(wf, step_id)
        if target_idx < 0:
            return {"error": f"Step '{step_id}' not found in workflow", "session_id": session_id}

        if step_id not in session["step_data"]:
            return {"error": f"Step '{step_id}' has not been completed yet", "session_id": session_id}

        previous_content = session["step_data"][step_id]

        steps_after = [s["id"] for s in wf["steps"][target_idx + 1:]]
        state.invalidate_steps_after(session_id, steps_after)

        state.update_session(session_id, current_step=step_id)

        return {
            "session_id": session_id,
            "revised_step": {"id": target_step["id"], "title": target_step["title"]},
            "previous_content": previous_content,
            "invalidated_steps": steps_after,
            "directive": target_step["directive_template"],
            "do_not": _DO_NOT_RULES,
            "gates": target_step["gates"],
        }

    @mcp.tool()
    def list_sessions() -> dict:
        """List all sessions with their status (active/completed)."""
        return {"sessions": state.list_sessions()}

    @mcp.tool()
    def delete_session(session_id: str) -> dict:
        """Delete a session regardless of state. Returns what was deleted."""
        try:
            deleted = state.delete_session(session_id)
        except KeyError as e:
            return {"error": str(e), "session_id": session_id}
        return {
            "session_id": deleted["session_id"],
            "workflow_type": deleted["workflow_type"],
            "current_step": deleted["current_step"],
            "completed": deleted["current_step"] == _COMPLETE,
        }

    @mcp.tool()
    def generate_artifact(session_id: str, output_format: str = "auto") -> dict:
        """Generate final artifact from completed workflow. Rejects if workflow is not complete.

        output_format controls the shape of the returned artifact:
        - "auto" (default): returns the raw content of the last step only.
        - "text": joins all step contents into a single string separated by double newlines.
        - "structured_code": returns a list of dicts, each with keys step_id, title, and content.
        """
        resolved, err = _resolve_session(session_id, workflows)
        if err:
            return err
        session, wf = resolved

        if session["current_step"] != _COMPLETE:
            idx, _ = _find_step(wf, session["current_step"])
            remaining = [s["title"] for s in wf["steps"][idx:]]
            return {
                "error": "Workflow not complete. Finish all steps first.",
                "session_id": session_id,
                "remaining_steps": remaining,
            }

        step_data = session["step_data"]

        if output_format == "auto":
            last_step_id = wf["steps"][-1]["id"]
            artifact: object = step_data.get(last_step_id, "")
        elif output_format == "structured_code":
            artifact = [
                {"step_id": s["id"], "title": s["title"], "content": step_data.get(s["id"], "")}
                for s in wf["steps"]
            ]
        else:
            artifact = "\n\n".join(step_data.get(s["id"], "") for s in wf["steps"])

        return {
            "session_id": session_id,
            "workflow_type": session["workflow_type"],
            "output_format": output_format,
            "artifact": artifact,
        }
