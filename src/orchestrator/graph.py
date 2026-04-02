from langgraph.graph import StateGraph
from src.orchestrator.state import GraphState
from src.agents.profiler import profiler_agent

builder = StateGraph(GraphState)

builder.add_node("profiler", profiler_agent)

builder.set_entry_point("profiler")

graph = builder.compile()