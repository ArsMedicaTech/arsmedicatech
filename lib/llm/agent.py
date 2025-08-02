"""
LLM Agent Module
"""
import enum
import json
from typing import (Any, Callable, Collection, Dict, List, Optional, Sequence,
                    Union, cast)

from openai import OpenAI
from openai.types.beta.threads.runs import ToolCall
from openai.types.chat import ChatCompletionMessageToolCall

from lib.llm.mcp_tools import fetch_mcp_tool_defs
from lib.services.encryption import get_encryption_service
from settings import logger

DEFAULT_SYSTEM_PROMPT = """
You are a clinical assistant that helps healthcare providers with patient care tasks.
You can answer questions, provide information, and assist with various healthcare-related tasks.
Your responses should be accurate, concise, and helpful.

You have access to tools that can help you provide better information. When you need to search for specific information or perform tasks that would benefit from using these tools, please use them. Don't hesitate to use tools when they would be helpful for providing accurate and comprehensive responses.
"""

tools_with_keys = ['rag']

from openai.types.chat import ChatCompletionToolParam

ToolDefinition = ChatCompletionToolParam

class LLMModel(enum.Enum):
    """
    Enumeration of supported LLM models.
    """
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"

    def __str__(self) -> str:
        return self.value

async def process_tool_call(
        tool_call: ToolCall,
        tool_dict: Dict[str, Callable[..., Any]],
        session_id: Optional[str] = None
    ) -> Dict[str, str]:
    """
    Process a tool call from the LLM and execute the corresponding function.
    :param tool_call: ToolCall object containing the function name and arguments.
    :param tool_dict: Dictionary mapping function names to callable functions.
    :param session_id: Optional session ID for tools that require it.
    :return: Dict containing the role, function name, and result content.
    """
    # Check if tool_call has function attribute (FunctionToolCall)
    if not hasattr(tool_call, 'function'):
        raise ValueError("Tool call does not have function attribute")
    
    function_name = tool_call.function.name # type: ignore
    arguments = json.loads(tool_call.function.arguments) # type: ignore
    for key, val in tool_dict.items():
        logger.debug(f"Tool: {key} -> {val}") # [DEBUG] Tool: _call -> <function fetch_mcp_tool_defs.<locals>.wrap.<locals>._call at 0x7f78720b23e0>
        logger.debug(f"Function: {function_name} -> {val.__name__}") # [DEBUG] Function: rag -> _call

    tool_function = tool_dict[function_name]
    # Check if this is an MCP tool by checking if it's a wrapped function from fetch_mcp_tool_defs
    # MCP tools are wrapped and always require session_id parameter
    if function_name in tools_with_keys or hasattr(tool_function, '__name__') and tool_function.__name__ == '_call':
        tool_result = await tool_function(session_id=session_id, **arguments)
    else:
        tool_result = await tool_function(**arguments)

    result = json.dumps(tool_result)

    return {"role": "function", "name": function_name, "content": result, "tool_call_id": tool_call.id}

class LLMAgent:
    """
    An agent that interacts with an LLM to perform tasks using tools.
    """
    def __init__(
            self,
            custom_llm_endpoint: Optional[str] = None,
            model: LLMModel = LLMModel.GPT_4_1_NANO,
            api_key: Optional[str] = None,
            system_prompt: str = DEFAULT_SYSTEM_PROMPT,
            **params: Dict[str, str]  # Additional parameters for the agent (e.g., temperature, max_tokens, etc.
    ) -> None:
        """
        Initialize the LLMAgent with the given parameters.
        :param custom_llm_endpoint: Endpoint for a custom LLM service (if any).
        :param model: LLMModel enum value representing the model to use.
        :param api_key: API key for accessing the LLM service.
        :param system_prompt: System prompt to set the context for the agent.
        :param params: Additional parameters for the agent, such as temperature, max_tokens, etc.
        :return: None
        """
        self.custom_llm_endpoint = custom_llm_endpoint
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.params = params  # Store additional parameters

        self.tool_definitions: List[ToolDefinition] = []
        self.tool_func_dict: Dict[str, Callable[..., Any]] = {}

        self.message_history: List[Dict[str, Union[str, Sequence[Collection[str]]]]] = self.fetch_history()

        if self.custom_llm_endpoint:
            # TODO...
            raise NotImplementedError("Custom LLM endpoint is not yet implemented.")
        if not self.api_key:
            raise ValueError("API key must be provided for LLM access.")

        self.client = OpenAI(api_key=self.api_key)

    def add_tool(self, tool_name: str, tool: Callable[..., Any], tool_def: ToolDefinition) -> None:
        """
        Add a tool to the agent.
        :param tool_name: Name of the tool to add.
        :param tool: Callable function that implements the tool's functionality.
        :param tool_def: Tool definition containing metadata about the tool.
        :return: None
        """
        if not callable(tool):
            raise ValueError("Tool must be a callable function.")
        self.tool_definitions.append(tool_def)
        self.tool_func_dict[tool_name] = tool

    def fetch_history(self) -> List[Dict[str, Union[str, Sequence[Collection[str]]]]]:
        """
        Fetch history from database.
        This method should be overridden to fetch conversation history from a database or other storage.
        :return: List of message history, starting with the system prompt.
        """
        # TODO.
        return [{"role": "system", "content": self.system_prompt}]

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the agent state to a dictionary for Flask session storage.
        :return: Dictionary containing the agent's state.
        """
        return {
            'message_history': self.message_history,
            'model': self.model.value,
            'system_prompt': self.system_prompt,
            'params': self.params
        }

    def reset_conversation(self) -> None:
        """
        Reset the conversation history while keeping system prompt.
        This method clears the message history but retains the system prompt.
        :return: None
        """
        self.message_history = [{"role": "system", "content": self.system_prompt}]

    @classmethod
    def from_dict(
            cls,
            data: Dict[str, Any],
            api_key: Optional[str] = None,
            tool_definitions: Optional[List[ToolDefinition]] = None,
            tool_func_dict: Optional[Dict[str, Callable[..., Any]]] = None
    ) -> 'LLMAgent':
        """
        Create an agent instance from serialized data.
        :param data: Dictionary containing serialized agent state.
        :param api_key: API key for accessing the LLM service.
        :param tool_definitions: List of tool definitions to restore.
        :param tool_func_dict: Dictionary mapping tool names to their callable functions.
        :return: An instance of LLMAgent with restored state.
        """
        model_value = data.get('model', LLMModel.GPT_4_1.value)
        model = LLMModel(model_value)
        
        agent = cls(
            model=model,
            api_key=api_key,
            system_prompt=data.get('system_prompt', DEFAULT_SYSTEM_PROMPT),
            **data.get('params', {})
        )
        
        # Restore message history
        message_history = data.get('message_history', [{"role": "system", "content": "You are a helpful assistant."}])
        if isinstance(message_history, list):
            # Cast to the more flexible type that matches fetch_history return type
            agent.message_history = cast(List[Dict[str, Union[str, Sequence[Collection[str]]]]], message_history)
        else:
            agent.message_history = [{"role": "system", "content": "You are a helpful assistant."}]
        
        # Restore tools if provided
        if tool_definitions and tool_func_dict:
            agent.tool_definitions = tool_definitions
            agent.tool_func_dict = tool_func_dict
        
        return agent

    @classmethod
    async def from_mcp(cls, mcp_url: str, api_key: str, model: Optional[LLMModel] = None, **kwargs: Dict[str, Any]) -> 'LLMAgent':
        """
        Build an LLMAgent that proxies every tool call to the given MCP server.
        :param mcp_url: URL of the MCP server to fetch tool definitions from.
        :param api_key: API key for accessing the LLM service.
        :param model: LLMModel enum value representing the model to use.
        :param kwargs: Additional parameters for the agent.
        :return: An instance of LLMAgent with tools fetched from the MCP server.
        """
        # 1) Discover tools from MCP
        defs, funcs = await fetch_mcp_tool_defs(mcp_url)

        # 2) Instantiate the agent with explicit parameters
        model_str = model.value if model else LLMModel.GPT_4_1_NANO.value
        
        system_prompt = kwargs.pop('system_prompt', DEFAULT_SYSTEM_PROMPT)
        if isinstance(system_prompt, dict):
            system_prompt = DEFAULT_SYSTEM_PROMPT
        
        agent = cls(
            custom_llm_endpoint=None,
            model=LLMModel(model_str),
            api_key=api_key,
            system_prompt=system_prompt,
            **kwargs
        )
        
        logger.debug(f"Found {len(defs)} tools from MCP server")
        for d in defs:
            name = d["function"]["name"]
            logger.debug("Adding tool:", d["function"]["name"], funcs[name], d)
            agent.add_tool(name, funcs[name], cast(ToolDefinition, d))
        
        if len(defs) == 0:
            logger.warning("No tools found from MCP server. Tool calls will not work.")
        return agent

    async def complete(self, prompt: Optional[str], **kwargs: Dict[str, str]) -> Dict[str, Any]:
        """
        Complete a prompt using the LLM, processing any tool calls if necessary.
        :param prompt: The user prompt to send to the LLM. If None, uses the existing message history.
        :param kwargs: Additional parameters for the LLM completion (e.g., temperature, max_tokens).
        :return: Dict containing the LLM's response and tool usage information.
        """
        if prompt:
            self.message_history.append({"role": "user", "content": prompt})

        if not self.api_key:
            raise ValueError("API key is required for LLM access.")
            
        api_key = get_encryption_service().encrypt_api_key(self.api_key)

        logger.debug("Sending request to OpenAI with model:", self.model.value)
        logger.debug("API Key:", api_key)

        if not api_key:
            raise ValueError("API key is required for LLM access.")

        # Convert message_history to ChatCompletionMessageParam format
        from openai.types.chat import ChatCompletionMessageParam

        def to_message_param(msg: Dict[str, Union[str, Sequence[Collection[str]]]]) -> ChatCompletionMessageParam:
            role = msg.get("role")
            content = msg.get("content")
            # Handle content that might be a complex type
            if isinstance(content, str):
                content_str = content
            else:
                content_str = str(content) if content else ""
            if role == "system":
                return cast(ChatCompletionMessageParam, {"role": "system", "content": content_str})
            elif role == "user":
                return cast(ChatCompletionMessageParam, {"role": "user", "content": content_str})
            elif role == "assistant":
                # Handle assistant messages with tool calls
                if "tool_calls" in msg:
                    return cast(ChatCompletionMessageParam, {
                        "role": "assistant", 
                        "content": content_str,
                        "tool_calls": msg["tool_calls"]
                    })
                else:
                    return cast(ChatCompletionMessageParam, {"role": "assistant", "content": content_str})
            elif role == "function":
                # Convert function role to tool role for API compatibility
                return cast(ChatCompletionMessageParam, {"role": "tool", "content": content_str, "tool_call_id": msg.get("tool_call_id", "")})
            else:
                raise ValueError(f"Unknown role: {role}")

        messages: List[ChatCompletionMessageParam] = [to_message_param(m) for m in self.message_history]

        logger.debug(f"Making OpenAI API call with {len(self.tool_definitions)} tools")
        logger.debug(f"Tool definitions: {self.tool_definitions}")
        
        completion = self.client.chat.completions.create(
            model=self.model.value,
            messages=messages,
            tools=self.tool_definitions,
            #tool_choice="auto",
            #tool_choice='required',
            extra_headers={
                "x-user-pw": api_key
            }
        )

        top_choice = completion.choices[0].message

        # process tool calls if any...
        tool_calls = top_choice.tool_calls
        logger.debug("Top choice:", top_choice)

        if tool_calls:
            # Track tool usage
            used_tools = [tool_call.function.name for tool_call in tool_calls]
            await self.process_tool_calls(tool_calls, top_choice.content or "")

            # Recurse to handle tool calls
            result = await self.complete(None, **kwargs)
            # Merge tool usage from recursive call
            if 'used_tools' in result:
                used_tools.extend(result['used_tools'])
            result['used_tools'] = used_tools
            return result
        else:
            # Add assistant response to message history
            content = top_choice.content or ""
            self.message_history.append({"role": "assistant", "content": content})

        return {"response": top_choice.content or "", "used_tools": []}

    async def process_tool_calls(self, tool_calls: List[ChatCompletionMessageToolCall], assistant_content: str = "") -> None:
        """
        Process a list of tool calls by executing the corresponding functions.
        :param tool_calls: List of ToolCall objects to process.
        :param assistant_content: Content of the assistant message that made the tool calls.
        :return: None
        """
        if not self.api_key:
            raise ValueError("API key is required for LLM access.")
            
        api_key = get_encryption_service().encrypt_api_key(self.api_key)

        logger.debug("Sending request to OpenAI with model:", self.model.value)
        logger.debug("API Key:", api_key)

        if not api_key: 
            raise ValueError("API key is required for LLM access.")

        # Process all tool calls and collect their results
        tool_results = []
        for tool_call in tool_calls:
            # Cast ChatCompletionMessageToolCall to ToolCall for compatibility
            tool_call_cast = cast(ToolCall, tool_call)
            result = await process_tool_call(tool_call_cast, self.tool_func_dict, session_id=api_key)
            tool_results.append(result)
        
        # Add assistant message with tool calls to history
        assistant_message = {
            "role": "assistant", 
            "content": assistant_content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in tool_calls
            ]
        }
        self.message_history.append(assistant_message)
        
        # Add tool responses to history
        for result in tool_results:
            self.message_history.append(cast(Dict[str, Union[str, Sequence[Collection[str]]]], result))

