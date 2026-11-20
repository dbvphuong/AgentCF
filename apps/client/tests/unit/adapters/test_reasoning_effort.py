"""Node reasoning level reaches the CLI without changing the Skill prompt."""
import json

import pytest

from agent_cf_client.execution.local_skill import execute_local_skill
from agent_cf_client.execution.process_manager import ProcessResult
from agent_cf_client.runtime.codex_adapter import CodexAdapter
from agent_cf_client.runtime.antigravity_adapter import AntigravityAdapter


@pytest.mark.parametrize("tool,level", [("codex","medium"),("codex","high"),("codex","xhigh"),("codex","max"),("antigravity","medium"),("antigravity","high")])
def test_local_node_level_is_a_cli_option_not_prompt_text(tmp_path, tool, level):
    source=tmp_path / "SKILL.md"
    source.write_text("Create output.txt for the topic.",encoding="utf-8")
    topic=tmp_path / "Topic 2"
    topic.mkdir()
    class PM:
        def run_process(self, **kw):
            command=kw["argv"]
            expected=f"Gọi skill {source}\ncho chủ đề {topic}"
            if tool=="codex":
                assert command[-1]==expected
                assert f'model_reasoning_effort="{level}"' in command
                stdout=json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"Saved"}})+"\n"+json.dumps({"type":"turn.completed"})
            else:
                assert command[command.index("-p")+1]==expected
                assert command[command.index("--effort")+1]==level
                stdout="Saved"
            (topic / "output.txt").write_text("Real fixture output",encoding="utf-8")
            return ProcessResult(0,stdout,"")
    adapter=(CodexAdapter if tool=="codex" else AntigravityAdapter)(process_manager=PM())
    task={"runner_id":"pc","working_directory":str(tmp_path),"skill_snapshot":{"source_path":str(source),"source_runner_id":"pc"},"runtime":{"adapter":tool,"model_id":"exact-model","reasoning_effort":level}}
    result,metadata=execute_local_skill(adapter=adapter,task=task,input_data={"topic_directory":str(topic)},runner_id="pc",log_dir=tmp_path / "logs",on_started=lambda _:None)
    assert result.success and metadata["local_files"][0]["path"]==str(topic / "output.txt")


def test_default_has_no_override_and_resume_keeps_selected_level(tmp_path):
    adapter=CodexAdapter()
    assert "-c" not in adapter.build_command(prompt="Skill",cwd=tmp_path)
    command=adapter.build_command(prompt="Skill",cwd=tmp_path,session_id="previous",reasoning_effort="high")
    assert "resume" in command and 'model_reasoning_effort="high"' in command
    agy=AntigravityAdapter()
    assert "--effort" not in agy.build_command(prompt="Skill")
    command=agy.build_command(prompt="Skill",session_id="previous",reasoning_effort="high")
    assert "--conversation=previous" in command and command[command.index("--effort")+1]=="high"


@pytest.mark.parametrize("adapter,level",[(CodexAdapter,"invalid"),(AntigravityAdapter,"max")])
def test_invalid_level_is_rejected_before_spawn(tmp_path,adapter,level):
    with pytest.raises(ValueError,match="Mức suy luận"):
        if adapter is CodexAdapter:
            adapter().build_command(prompt="Skill",cwd=tmp_path,reasoning_effort=level)
        else:
            adapter().build_command(prompt="Skill",reasoning_effort=level)
