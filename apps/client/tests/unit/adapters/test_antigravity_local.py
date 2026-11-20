"""Antigravity file execution uses the Project cwd and actual local output checks."""
import pytest

from agent_cf_client.execution.local_skill import execute_local_skill
from agent_cf_client.execution.process_manager import ProcessResult
from agent_cf_client.runtime.antigravity_adapter import AntigravityAdapter


@pytest.mark.parametrize("mode", ["file", "chat_only", "timeout", "cancelled", "fallback", "failed"])
def test_local_execution(tmp_path, mode):
    work=tmp_path / "Project"
    topic=work / "Chủ đề 2"
    topic.mkdir(parents=True)
    source=work / "SKILL.md"
    source.write_text("Create output.txt for the given topic.",encoding="utf-8")
    logs=tmp_path / "control"
    seen=[]
    class PM:
        def run_process(self, **kwargs):
            argv=kwargs["argv"]
            assert argv[argv.index("-p")+1] == f"Gọi skill {source}\ncho chủ đề {topic.resolve()}"
            assert kwargs["cwd"] == work.resolve()
            assert argv[argv.index("--add-dir")+1] == str(work.resolve())
            assert "--sandbox" not in argv and "--dangerously-skip-permissions" in argv
            assert argv[argv.index("--model")+1] == "gemini-3.8-flash-high"
            assert argv[argv.index("--print-timeout")+1] == "17s"
            assert kwargs["stdout_path"].parent == logs
            kwargs["on_started"](321)
            if mode == "file":
                (topic / "output.txt").write_text("Created by CLI tools",encoding="utf-8")
            if mode == "fallback":
                return ProcessResult(0,"Failed to resolve model flag","")
            return ProcessResult(1 if mode=="failed" else 0,"Created output", "",timed_out=mode=="timeout",cancelled=mode=="cancelled")
    task={"runner_id":"pc","working_directory":str(work),"skill_snapshot":{"source_path":str(source),"source_runner_id":"pc"},"runtime":{"adapter":"antigravity","model_id":"gemini-3.8-flash-high"},"execution_timeout_seconds":17}
    logs.mkdir()
    result, metadata=execute_local_skill(adapter=AntigravityAdapter(process_manager=PM()),task=task,input_data={"topic_directory":str(topic)},runner_id="pc",log_dir=logs,on_started=seen.append)
    assert seen==[321]
    assert result.success == (mode=="file")
    if mode=="file":
        assert metadata["local_files"][0]["path"]==str(topic / "output.txt")
    else:
        assert result.error_code=={"chat_only":"local_output_missing","timeout":"timeout","cancelled":"cancelled","fallback":"unsupported_model","failed":"non_zero_exit"}[mode]


def test_local_execution_can_resume(tmp_path):
    class PM:
        def run_process(self, **kwargs):
            assert "--conversation=previous" in kwargs["argv"]
            return ProcessResult(0,"Continued","")
    result=AntigravityAdapter(process_manager=PM()).execute_local_skill(prompt="Continue",cwd=tmp_path,model="gemini-3.8-flash-high",timeout_seconds=5,log_dir=tmp_path / "logs",session_id="previous")
    assert result.success and result.session_id=="previous"
