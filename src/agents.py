import json
import re
from typing import TypedDict, Optional, List, Dict, Any
from dotenv import load_dotenv, find_dotenv
import os

# LANGCHAIN
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# MAS 
from .memory import Memory
from .prompts import ROUTER_PROMPT, DECOMPOZER_PROMPT, CODE_ASSISTANT_PROMPT, STUDY_ASSISTANT_PROMPT, PLANNER_PROMPT
from .utils import AVAILABLE_TOOLS, apply_tools, get_available_tools, run_tool, extract_tool_calls


# === MODEL INITIALIZATION ===
load_dotenv(find_dotenv(usecwd=True))

BASE_URL = os.getenv("LITELLM_BASE_URL", "http://a6k2.dgx:34000/v1")
API_KEY = os.getenv("LITELLM_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-32b")

BASE_LLM = ChatOpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL_NAME
    )


# === STATE ===
class State(TypedDict):
    """
    Shared state object passed between agents in the multi-agent workflow.

    Attributes:
        query: Original user query.
        category: High-level category assigned by the router (e.g. academic, programming, planning, other).
        memory: List of memory/profile notes relevant to the current query.
        execution_plan: Decomposed plan or list of subtasks for the query.
        agent_log: Per-agent logs of intermediate outputs and tool usage.
        final_answer: Final response to the user after all agents finish.
    """

    query: str
    category: Optional[str]
    memory: List[Dict]
    execution_plan: Optional[str]
    agent_log: Dict[str, str]
    final_answer: Optional[str]


# === ROUTER AGENT ===
class RouterAgent:
    """
    Agent responsible for classifying the user query into a high-level category.

    Uses ROUTER_PROMPT to map the query to one of the predefined categories
    (e.g. academic, programming, planning, other) and stores the decision in state["category"].
    """

    def __init__(self, llm=BASE_LLM):
        self.llm = llm
        prompt = PromptTemplate(
            input_variables=["query"],
            template=ROUTER_PROMPT
            )

        self.chain = prompt | self.llm | StrOutputParser()

    def run(self, state: State) -> State:
        result = self.chain.invoke({"query": state["query"]})

        text = result.lower()
        if "academic" in text:
            state["category"] = "academic"
        elif "programming" in text:
            state["category"] = "programming"
        elif "planning" in text:
            state["category"] = "planning"
        else:
            state["category"] = "other"

        state.setdefault("agent_log", {})
        state["agent_log"]["router"] = result

        return state


# === DECOMPOZER AGENT ===
class DecompozerAgent:
    """
    Agent that decomposes the user query into an execution plan or list of subtasks.

    Uses DECOMPOZER_PROMPT to generate a structured plan stored in state["execution_plan"].
    """

    def __init__(self, llm=BASE_LLM):
        self.llm = llm

        prompt = PromptTemplate(
            input_variables=["query"],
            template=DECOMPOZER_PROMPT
            )

        self.chain = prompt | self.llm | StrOutputParser()

    def run(self, state: State) -> State:
        execution_plan = self.chain.invoke({"query": state["query"]})
        state["execution_plan"] = execution_plan
        state["agent_log"]["execution_plan"] = execution_plan

        return state


# === CODE ASSISTANT AGENT ===
class CodeAssistantAgent:
    """
    Agent that provides coding help based on the query and prepared execution plan.

    Uses CODE_ASSISTANT_PROMPT along with available tools. May emit tool call markers,
    which are executed and inlined into the final response.
    """

    def __init__(self, llm=BASE_LLM):
        self.llm = llm
        
        prompt = PromptTemplate(
            input_variables=["query", "execution_plan", "tools"],
            template=CODE_ASSISTANT_PROMPT
        )
        self.chain = prompt | self.llm | StrOutputParser()

    def run(self, state: State) -> State:
        execution_plan = state.get("execution_plan", "")
        tools = get_available_tools()
        
        result = self.chain.invoke({
            "query": state["query"],
            "execution_plan": execution_plan,
            "tools": tools
        })

        processed, executed = apply_tools(result)

        state["agent_log"]["code_assistant"] = processed
        state["agent_log"]["code_assistant_tools"] = executed

        return state


# === STUDY ASSISTANT AGENT ===
class StudyAssistantAgent:
    """
    Agent that helps with academic/theoretical questions using user profile memory.

    Uses STUDY_ASSISTANT_PROMPT, optional Memory, and available tools. Tool calls
    are detected and executed, with results inlined into the final output.
    """

    def __init__(self, llm=BASE_LLM, memory: Memory = None):
        self.llm = llm
        self.memory = memory

        prompt = PromptTemplate(
            input_variables=["query", "memory", "tools"],
            template=(STUDY_ASSISTANT_PROMPT)
        )

        self.chain = prompt | self.llm | StrOutputParser()

    def run(self, state: State) -> State:
        # profile_info = []
        if self.memory:
            profile_info = self.memory.get_from_profile(state["query"]) or []

        memory_str = "\n".join([
            f"{n.get('title','')}: {n.get('content','')}" for content in profile_info
        ])

        tools = get_available_tools()

        result = self.chain.invoke({
            "query": state["query"],
            "memory": memory_str,
            "tools": tools
        })

        processed, executed = apply_tools(result)

        state["agent_log"]["study_assistant"] = processed
        state["agent_log"]["study_assistant_tools"] = executed
        state["memory"] = profile_info

        return state


# === PLANNER AGENT ===
class PlannerAgent:
    """
    Agent that creates schedules and step-by-step plans based on the user query.

    Uses PLANNER_PROMPT and optional memory context about upcoming events or constraints.
    """
    def __init__(self, llm=BASE_LLM, profile_notes=None):
        self.llm = llm
        self.profile_notes = profile_notes

        prompt = PromptTemplate(
            input_variables=["query", "tools"],
            partial_variables={"profile_notes": str(self.profile_notes)},
            template=PLANNER_PROMPT
        )

        self.chain = prompt | self.llm | StrOutputParser()

    def run(self, state: State) -> State:
        tools = get_available_tools()
        
        result = self.chain.invoke({
            "query": state["query"],
            "tools": tools
        })

        processed, executed = apply_tools(result)

        state["agent_log"]["planner"] = processed
        state["agent_log"]["planner_tools"] = executed

        return state