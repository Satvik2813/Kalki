"""Contracts: serialisation round-trips and plan queries."""
from shared.contracts import (
    AgentState,
    ExecutionStatus,
    Plan,
    Task,
    TaskStatus,
    ToolResult,
)


def test_task_roundtrip():
    t = Task(id="task-1", description="do a thing", tool="read_file",
             tool_args={"path": "x"})
    t.result = ToolResult.success("read_file", output="hi")
    back = Task.from_dict(t.to_dict())
    assert back.id == t.id
    assert back.tool == "read_file"
    assert back.result and back.result.ok


def test_plan_next_task_respects_dependencies():
    plan = Plan(objective="o", tasks=[
        Task(id="a", description="a"),
        Task(id="b", description="b", depends_on=["a"]),
    ])
    # b is blocked until a completes
    assert plan.next_task().id == "a"
    plan.get("a").status = TaskStatus.COMPLETED
    assert plan.next_task().id == "b"


def test_plan_complete_and_failure_flags():
    plan = Plan(objective="o", tasks=[Task(id="a", description="a")])
    assert not plan.is_complete()
    plan.get("a").status = TaskStatus.COMPLETED
    assert plan.is_complete()
    assert not plan.has_failure()


def test_agent_state_roundtrip():
    st = AgentState(objective="fix bug")
    st.plan = Plan(objective="fix bug", tasks=[Task(id="a", description="a")])
    st.status = ExecutionStatus.RUNNING
    d = st.to_dict()
    back = AgentState.from_dict(d)
    assert back.objective == "fix bug"
    assert back.plan and back.plan.tasks[0].id == "a"


def test_tool_result_failure_carries_classification():
    from shared.contracts import FailureClass
    r = ToolResult.failure("t", "boom", FailureClass.TRANSIENT)
    assert not r.ok
    assert r.failure_class == FailureClass.TRANSIENT
    assert ToolResult.from_dict(r.to_dict()).failure_class == FailureClass.TRANSIENT
