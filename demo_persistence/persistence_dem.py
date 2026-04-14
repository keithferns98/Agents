from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

llm =  init_chat_model(
    model = os.getenv("MODEL_NAME"),
    api_key = os.getenv("OPENROUTER_API_KEY"),
    model_provider="openrouter",
    base_url = "https://openrouter.ai/api/v1",
    temperature = 0
)

class JokeState(TypedDict):
    topic: str
    joke: str
    explaination: str


def generate_joke(state: JokeState)-> dict:
    prompt = f"generate a joke on the given topic {state["topic"]}."
    response = llm.invoke(prompt).content
    return {"joke": response}

def generate_explaination(state: JokeState)-> dict:
    prompt = f"generate an explaination for the given joke - {state["joke"]}"
    response = llm.invoke(prompt).content
    return {"explaination": response}


graph = StateGraph(JokeState)

graph.add_node("generate_joke", generate_joke)
graph.add_node("generate_explaination", generate_explaination)

graph.add_edge(START, "generate_joke")
graph.add_edge("generate_joke", "generate_explaination")
graph.add_edge("generate_explaination", END)

checkpointer = InMemorySaver()
workflow = graph.compile(checkpointer= checkpointer)

config1 = {"configurable": {"thread_id": 1}}
workflow.invoke({"topic": "Marvel"}, config = config1)

print(workflow.get_state(config1))
print("-"*20)
workflows =  list(workflow.get_state_history(config1))
print(workflows[-2])

# print(workflow.get_state({"configurable":{"thread_id": 1, "checkpoint_id": workflows[-2]}}))