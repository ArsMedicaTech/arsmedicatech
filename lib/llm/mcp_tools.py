"""
Fetch and convert MCP tool definitions to OpenAI function format.
"""
from typing import Any, Callable, Dict, List, Tuple

import httpx
from fastmcp.client import Client

from settings import logger


class CustomHeaderAuth(httpx.Auth):
    def __init__(self, headers: dict[str, str]) -> None:
        """
        Custom authentication class to add headers to HTTP requests.
        :param headers: Dictionary of headers to include in the request.
        :type headers: dict[str, str]
        :return: None
        """
        self.headers = headers

    from typing import Generator

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """
        Add custom headers to the request.
        :param request: The HTTP request to modify.
        :type request: httpx.Request
        :return: The modified request with custom headers.
        :rtype: Generator[httpx.Request, httpx.Response, None]
        """
        for key, value in self.headers.items():
            request.headers[key] = value
        yield request



async def fetch_mcp_tool_defs(mcp_url: str) -> Tuple[List[Dict[str, Any]], Dict[str, Callable[..., Any]]]:
    """
    • Pull the tool list from an MCP server
    • Convert each tool's JSON-Schema → OpenAI 'tool' format
    • Return (openai_tool_defs, {tool_name: call_function})

    :param mcp_url: URL of the MCP server to fetch tools from.
    :type mcp_url: str
    :return: A tuple containing a list of OpenAI tool definitions and a dictionary mapping tool names to their call functions.
    :rtype: tuple[list[dict], dict]
    """
    try:
        async with Client(mcp_url) as c:
            logger.debug('Fetching tools from MCP server:', mcp_url)
            logger.debug(str(c.__dir__()))
            #tools = (await c.tools.list()).tools   # dict[name → Tool]
            tools = (await c.list_tools())  # [Tool]
            logger.debug('tools', tools)
    except Exception as e:
        logger.error(f'Error connecting to MCP server at {mcp_url}: {e}')
        logger.error('MCP server may not be running or accessible')
        tools = []

    openai_defs: list[Dict[str, Any]] = []
    func_lookup: dict[str, Callable[..., Any]] = {}

    # Per‑tool wrapper that calls MCP via the Python client
    def wrap(tool_name: str) -> Callable[..., Any]:
        """
        Create a wrapper function for calling a specific tool.
        :param tool_name: Name of the tool to wrap.
        :return: Callable function that takes session_id and other arguments to call the tool.
        """
        async def _call(*, session_id: str, **kwargs: Any) -> Any:
            custom_auth = CustomHeaderAuth({
                "x-user-id": "optional to add later...",
                "x-session-token": session_id
            })

            async with Client(mcp_url, auth=custom_auth) as c:
                # 'call_tool_mcp', 'call_tool'
                #result = await c.tools.call(name=tool_name, arguments=kwargs)
                # result = await client.call_tool("my_tool", {"param": "value"})
                logger.debug(f"Calling tool: {tool_name} with args:", kwargs)
                result = await c.call_tool(tool_name, kwargs)
                logger.debug(f"Tool call result for {tool_name}:", result)
                if hasattr(result, 'structured_content'):
                    return result.structured_content or result.content
                else:
                    return result.content or result
        return _call

    tool_dict = {tool.name: tool for tool in tools}

    for name, tool in tool_dict.items():
        openai_defs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool.description or "",
                #"parameters": tool.parameters
                "parameters": {
                    "type": "object",
                    "properties": tool.inputSchema.get("properties", {}),
                    "required": tool.inputSchema.get("required", []),
                }
            }
        })
        func_lookup[name] = wrap(name)

    return openai_defs, func_lookup
