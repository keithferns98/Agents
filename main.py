from langgraph.graph import StateGraph
from demo_src.demo_state import MessagesState
from demo_src.demo_model_node import llm_call
from demo_src.demo_tool_node import tool_node
from langgraph.graph import StateGraph, START, END
from demo_src.demo_endlogic import should_continue
from langchain.messages import HumanMessage

agent_builder = StateGraph(MessagesState)

#Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

#Add edges to connect node
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call",
                                    should_continue,
                                    ["tool_node", END])
agent_builder.add_edge("tool_node", "llm_call")

agent = agent_builder.compile()
messages = [HumanMessage(content = "Add 3 and 4.")]
messages = agent.invoke({"messages": messages})
for m in messages["messages"]:
    m.pretty_print()


