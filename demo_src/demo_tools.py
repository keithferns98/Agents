from langchain.tools import tool
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os

load_dotenv()

model = init_chat_model(
    model = os.getenv("MODEL_NAME"),
    api_key = os.getenv("OPENROUTER_API_KEY"),
    model_provider="openrouter",
    base_url = "https://openrouter.ai/api/v1",
    temperature = 0
)
@tool
def multiply(a: int, b: int)-> int:
    """
    Multiply `a` and `b`
    Args:
        a: First int
        b: Second int
    """
    return a*b

@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`
    Args:
        a: First int
        b: Second int
    """
    return  a + b

@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b

tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)
# response = model.invoke("Hello!")
# print(response.content)