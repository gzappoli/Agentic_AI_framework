import asyncio
from langgraph.graph import StateGraph
from typing import TypedDict

# ---- Import nodes ----
from cv_parser import cv_parser_node, get_input_node
from job_search_agents import scrape_jobs_node, save_results_node
from matcher import match_node
from writer import write_csv_node

# ---- Define your LangGraph State ----
class PipelineState(TypedDict):
    cv_path: str
    user_input: str
    locations: str
    cv_data: dict
    found_jobs: list
    

# ---- Build the LangGraph ----
def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("get_input", get_input_node)
    graph.add_node("cv_parser", cv_parser_node)
    graph.add_node("scrape_jobs", scrape_jobs_node)
    graph.add_node("save_results", save_results_node)
    graph.add_node("match", match_node)
    graph.add_node("write_csv", write_csv_node)

    graph.set_entry_point("get_input")
    graph.add_edge("get_input", "cv_parser")
    graph.add_edge("cv_parser", "scrape_jobs")
    graph.add_edge("scrape_jobs", "save_results")
    graph.add_edge("scrape_jobs", "match")
    graph.add_edge("match", "write_csv")


    return graph.compile()

# ---- Run it ----
if __name__ == "__main__":
    pipeline = build_graph()
    asyncio.run(pipeline.ainvoke({
        "cv_path": "data/cv.pdf"
    }))
