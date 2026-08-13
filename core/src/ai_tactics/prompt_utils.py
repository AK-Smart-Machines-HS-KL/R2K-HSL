"""Shared prompt utilities used by setup_r2k.py and r2k_evaluator.py.

Extracted from duplicated code in both files (Phase C cleanup, v6.4 spec).
"""

import json
import re


def clean_json_samples(content, explain_active):
    """Transform sample OUTPUT blocks: inject or strip analysis/oracle keys.

    Scans for 'OUTPUT:' markers followed by JSON blocks. For each block:
    - If explain_active: ensures 'analysis' and 'oracle' keys exist (injects
      context-appropriate defaults if missing), keeps 'assignments'.
    - If not explain_active: strips 'analysis' and 'oracle', keeps 'assignments'.

    Context-specific default values are selected based on keywords found in
    the 300 chars before the OUTPUT: marker (DEFENSIVE PASS, CLEARANCE,
    ANTI-CLUSTERING, BOUNDARY STAGING).
    """
    pattern = r'OUTPUT:\s*'
    matches = list(re.finditer(pattern, content))
    if not matches:
        return content
    output = ""
    last_idx = 0
    for m in matches:
        start_pos = m.start()
        end_pos = m.end()
        output += content[last_idx:start_pos]
        brace_count = 0
        json_start = -1
        json_end = -1
        for idx in range(end_pos, len(content)):
            char = content[idx]
            if char == '{':
                if brace_count == 0:
                    json_start = idx
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = idx + 1
                    break
        if json_start == -1 or json_end == -1:
            output += content[start_pos:end_pos]
            last_idx = end_pos
            continue
        raw_json = content[json_start:json_end]
        before_text = content[max(0, start_pos - 300):start_pos]
        analysis_val = "Tactical assessment of entity positions and ball trajectory."
        oracle_val = "Predictive optimization of team response to secure match advantage."
        if "DEFENSIVE PASS" in before_text or "CLEARANCE" in before_text:
            analysis_val = "blue_1 clears the ball from the defensive zone towards blue_2."
            oracle_val = "Passing the ball out of danger into the midfield."
        elif "ANTI-CLUSTERING" in before_text:
            analysis_val = "blue_1 attacks the ball while blue_2 drops back to support and avoid clustering."
            oracle_val = "Maintain optimal distance between teammates to control the field."
        elif "BOUNDARY STAGING" in before_text:
            analysis_val = "blue_1 moves to intercept the ball near the boundary while blue_2 guards the goal."
            oracle_val = "Secure the defensive line to prevent any immediate shots on goal."
        try:
            data = json.loads(raw_json)
        except Exception:
            try:
                sanitized = re.sub(r'\n\s*', ' ', raw_json)
                data = json.loads(sanitized)
            except Exception:
                data = {}

        if explain_active:
            new_data = {}
            new_data["analysis"] = data.get("analysis", analysis_val)
            new_data["oracle"] = data.get("oracle", oracle_val)
            if "assignments" in data:
                new_data["assignments"] = data["assignments"]
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data["assignments"] = data
            formatted_json = json.dumps(new_data, indent=2)
        else:
            if "assignments" in data:
                new_data = {"assignments": data["assignments"]}
            else:
                data.pop("analysis", None)
                data.pop("oracle", None)
                new_data = {"assignments": data}
            formatted_json = json.dumps(new_data, indent=2)
        output += "OUTPUT: " + formatted_json
        last_idx = json_end
    output += content[last_idx:]
    return output