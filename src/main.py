from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END

from .memory import Memory
from .agents import (
    RouterAgent,
    DecompozerAgent,
    CodeAssistantAgent,
    StudyAssistantAgent,
    PlannerAgent
)

# === STATE ===
class State(TypedDict):
    query: str
    category: Optional[str]
    memory: Any
    execution_plan: Optional[str]
    agent_log: Dict[str, str]
    final_answer: Optional[str]
    profile_notes: Optional[List[Any]]


def choose_agent(state: State) -> str:
    cat = state["category"]

    if cat == "academic":
        return "academic"
    if cat == "programming":
        return "decompozer"
    if cat == "planning":
        return "planning"
    return "other"


# === NODES ===
def router_node(state: State) -> State:
    router = RouterAgent()

    return router.run(state)


def decompozer_node(state: State) -> State:
    decompozer = DecompozerAgent()

    return decompozer.run(state)


def code_assistant_node(state: State) -> State:
    memory = state["memory"]
    code_assistant = CodeAssistantAgent(memory=memory)
    result = code_assistant.run(state)
    result["final_answer"] = result["agent_log"]["code_assistant"]

    return result


def study_assistant_node(state: State) -> State:
    memory = state["memory"]
    study_assistant = StudyAssistantAgent(memory=memory)

    result = study_assistant.run(state)
    result["final_answer"] = result["agent_log"]["study_assistant"]

    return result


def planner_node(state: State) -> State:
    memory = state["memory"]
    profile_notes = state["profile_notes"]
    planner = PlannerAgent(profile_notes=profile_notes, memory=memory)
    result = planner.run(state)
    result["final_answer"] = result["agent_log"]["planner"]

    return result


def reserve_node(state: State) -> State:
    memory = state["memory"]
    reserve_agent = StudyAssistantAgent(memory=memory)

    result = reserve_agent.run(state)
    result["final_answer"] = result["agent_log"]["study_assistant"]

    return result


def build_graph():
    workflow = StateGraph(State)

    workflow.add_node("router", router_node)
    workflow.add_node("decompozer", decompozer_node)
    workflow.add_node("code_assistant", code_assistant_node)
    workflow.add_node("study_assistant", study_assistant_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("other", reserve_node)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        choose_agent,
        {
            "academic": "study_assistant",
            "decompozer": "decompozer",
            "planning": "planner",
            "other": "other"
        }
    )

    workflow.add_edge("decompozer", "code_assistant")

    workflow.add_edge("study_assistant", END)
    workflow.add_edge("code_assistant", END)
    workflow.add_edge("planner", END)
    workflow.add_edge("other", END)

    return workflow.compile()  
    

def run(query: str, memory_path: str = "src/memory.json"):
    memory = Memory(memory_path)
    profile_notes = memory.get_from_profile("event")

    state: State = {
        "query": query,
        "category": None,
        "memory": memory,
        "execution_plan": None,
        "agent_log": {},
        "final_answer": None,
        "profile_notes": profile_notes,
    }

    graph = build_graph()

    result = graph.invoke(state)

    memory.update_history(query, result["final_answer"] or "")

    return result
