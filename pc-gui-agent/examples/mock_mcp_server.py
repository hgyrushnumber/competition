"""
简单的MCP服务器模拟器（用于测试）
模拟MCP服务器响应，实现基本的文件读写工具
"""
import json
import sys
import asyncio
from pathlib import Path


async def read_line():
    """异步读取一行输入"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)


async def write_line(data):
    """异步写入一行输出"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: (sys.stdout.write(data), sys.stdout.flush()))


async def mock_mcp_server():
    """模拟MCP服务器"""
    try:
        # 读取初始化请求
        init_request_str = await read_line()
        if not init_request_str:
            return
        
        init_request = json.loads(init_request_str.strip())
        
        # 发送初始化响应
        init_response = {
            "jsonrpc": "2.0",
            "id": init_request["id"],
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mock-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
        await write_line(json.dumps(init_response) + "\n")
        
        # 处理工具列表请求
        tools_request_str = await read_line()
        if not tools_request_str:
            return
        
        tools_request = json.loads(tools_request_str.strip())
        
        # 定义可用工具
        tools_response = {
            "jsonrpc": "2.0",
            "id": tools_request["id"],
            "result": {
                "tools": [
                    {
                        "name": "read_file",
                        "description": "读取文件内容",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "要读取的文件路径"
                                }
                            },
                            "required": ["path"]
                        }
                    },
                    {
                        "name": "write_file",
                        "description": "写入文件内容",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "要写入的文件路径"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "要写入的文件内容"
                                }
                            },
                            "required": ["path", "content"]
                        }
                    },
                    {
                        "name": "list_directory",
                        "description": "列出目录内容",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "要列出的目录路径"
                                }
                            },
                            "required": ["path"]
                        }
                    }
                ]
            }
        }
        await write_line(json.dumps(tools_response) + "\n")
        
        # 处理工具调用请求
        while True:
            request_str = await read_line()
            if not request_str:
                break
            
            request = json.loads(request_str.strip())
            
            # 处理tools/list请求
            if request.get("method") == "tools/list":
                # 返回工具列表（与初始化时相同）
                list_response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "read_file",
                                "description": "读取文件内容",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "要读取的文件路径"
                                        }
                                    },
                                    "required": ["path"]
                                }
                            },
                            {
                                "name": "write_file",
                                "description": "写入文件内容",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "要写入的文件路径"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "要写入的文件内容"
                                        }
                                    },
                                    "required": ["path", "content"]
                                }
                            },
                            {
                                "name": "list_directory",
                                "description": "列出目录内容",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "要列出的目录路径"
                                        }
                                    },
                                    "required": ["path"]
                                }
                            }
                        ]
                    }
                }
                await write_line(json.dumps(list_response) + "\n")
                continue
            
            # 处理tools/call请求
            if request.get("method") == "tools/call":
                tool_name = request["params"]["name"]
                args = request["params"]["arguments"]
                
                # 模拟工具执行
                result = None
                error = None
                
                try:
                    if tool_name == "read_file":
                        file_path = Path(args["path"])
                        if file_path.exists() and file_path.is_file():
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            result = {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": content
                                    }
                                ]
                            }
                        else:
                            error = {
                                "code": -32602,
                                "message": f"文件不存在或不是文件: {args['path']}"
                            }
                    
                    elif tool_name == "write_file":
                        file_path = Path(args["path"])
                        # 确保目录存在
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(args["content"])
                        
                        result = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"成功写入文件: {args['path']}"
                                }
                            ]
                        }
                    
                    elif tool_name == "list_directory":
                        dir_path = Path(args["path"])
                        if dir_path.exists() and dir_path.is_dir():
                            items = []
                            for item in dir_path.iterdir():
                                item_type = "目录" if item.is_dir() else "文件"
                                items.append(f"{item_type}: {item.name}")
                            
                            result = {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "\n".join(items) if items else "目录为空"
                                    }
                                ]
                            }
                        else:
                            error = {
                                "code": -32602,
                                "message": f"目录不存在: {args['path']}"
                            }
                    
                    else:
                        error = {
                            "code": -32601,
                            "message": f"未知工具: {tool_name}"
                        }
                
                except Exception as e:
                    error = {
                        "code": -32603,
                        "message": f"工具执行错误: {str(e)}"
                    }
                
                # 发送响应
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"]
                }
                
                if error:
                    response["error"] = error
                else:
                    response["result"] = result
                
                await write_line(json.dumps(response) + "\n")
            
            else:
                # 未知方法
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"未知方法: {request.get('method')}"
                    }
                }
                await write_line(json.dumps(response) + "\n")
    
    except Exception as e:
        # 发生错误时，尝试发送错误响应
        try:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"服务器内部错误: {str(e)}"
                }
            }
            await write_line(json.dumps(error_response) + "\n")
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(mock_mcp_server())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.stderr.write(f"Mock MCP Server Error: {e}\n")
        sys.exit(1)

