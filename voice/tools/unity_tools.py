"""
Unity Tools for DEVA - Direct Unity Editor control via Coplay unity-mcp server.

Uses HTTP JSON-RPC to communicate with the unity-mcp MCP server running
inside the Unity Editor. Gives DEVA the ability to create GameObjects,
add components, manage scenes, control playback, and more.

MCP Server: Coplay unity-mcp (localhost:8080/mcp)
Protocol: JSON-RPC 2.0 via HTTP POST
"""

import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import httpx


@dataclass
class UnityBridgeConfig:
    """Configuration for Unity MCP bridge."""
    host: str = "localhost"
    port: int = 8080
    endpoint: str = "/mcp"
    timeout: float = 10.0
    health_cache_ttl: float = 30.0  # Cache health check for 30s


class UnityBridge:
    """
    Bridge between DEVA and Unity Editor via MCP server.

    Handles:
    - Connection management with cached health checks
    - JSON-RPC 2.0 calls to the MCP server
    - Graceful degradation when Unity is not running
    """

    def __init__(self, config: UnityBridgeConfig = None):
        self.config = config or UnityBridgeConfig()
        self._base_url = f"http://{self.config.host}:{self.config.port}{self.config.endpoint}"
        self._rpc_id = 0
        self._health_ok = False
        self._health_checked_at = 0.0

    @property
    def is_connected(self) -> bool:
        """Check if Unity MCP server is reachable (cached)."""
        now = time.time()
        if now - self._health_checked_at < self.config.health_cache_ttl:
            return self._health_ok
        return self._check_health()

    def _check_health(self) -> bool:
        """Ping the MCP server to check if it's alive."""
        try:
            with httpx.Client(timeout=3.0) as client:
                # Use a lightweight RPC call to test connectivity
                resp = client.post(self._base_url, json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": self._next_id()
                })
                self._health_ok = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, OSError):
            self._health_ok = False

        self._health_checked_at = time.time()
        return self._health_ok

    def _next_id(self) -> int:
        """Generate next JSON-RPC request ID."""
        self._rpc_id += 1
        return self._rpc_id

    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """
        Call an MCP tool on the Unity server.

        Args:
            tool_name: MCP tool name (e.g., "manage_gameobject")
            arguments: Tool arguments dict

        Returns:
            Result string from MCP server, or error message
        """
        if not self.is_connected:
            return "Error: Unity MCP server not reachable. Is Unity open with the MCP plugin?"

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": self._next_id()
        }

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                resp = client.post(self._base_url, json=payload)

            if resp.status_code != 200:
                return f"Error: MCP server returned HTTP {resp.status_code}"

            data = resp.json()

            # Check for JSON-RPC error
            if "error" in data:
                err = data["error"]
                return f"Error: {err.get('message', 'Unknown MCP error')} (code {err.get('code', '?')})"

            # Extract result
            result = data.get("result", {})

            # MCP tool results have a "content" array with text blocks
            if isinstance(result, dict) and "content" in result:
                parts = []
                for block in result["content"]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                return "\n".join(parts) if parts else json.dumps(result, indent=2)

            return json.dumps(result, indent=2) if result else "(no output)"

        except httpx.ConnectError:
            self._health_ok = False
            self._health_checked_at = time.time()
            return "Error: Cannot connect to Unity MCP server. Is Unity running?"
        except httpx.TimeoutException:
            return "Error: Unity MCP server timed out. The editor might be busy."
        except Exception as e:
            return f"Error: {str(e)}"

    def invalidate_cache(self):
        """Force a fresh health check on next call."""
        self._health_checked_at = 0.0

    def get_status(self) -> str:
        """Get human-readable connection status."""
        connected = self._check_health()
        if connected:
            return f"Connected to Unity MCP at {self._base_url}"
        return f"Not connected (tried {self._base_url})"


# === Tool wrapper functions ===
# Each function maps to a Claude tool and calls the appropriate MCP tool.

def unity_gameobject(bridge: UnityBridge, action: str, name: str,
                     parent: str = None, position: str = None,
                     rotation: str = None, scale: str = None) -> str:
    """Manage GameObjects — create, delete, rename, move."""
    args = {"action": action, "name": name}
    if parent:
        args["parent"] = parent
    if position:
        args["position"] = position
    if rotation:
        args["rotation"] = rotation
    if scale:
        args["scale"] = scale
    return bridge.call_tool("manage_gameobject", args)


def unity_component(bridge: UnityBridge, action: str, gameobject: str,
                    component_type: str = None, properties: str = None) -> str:
    """Manage Components — add, remove, get, modify."""
    args = {"action": action, "gameobject": gameobject}
    if component_type:
        args["component_type"] = component_type
    if properties:
        args["properties"] = properties
    return bridge.call_tool("manage_component", args)


def unity_scene(bridge: UnityBridge, action: str,
                scene_name: str = None) -> str:
    """Manage Scenes — load, save, get hierarchy, new."""
    args = {"action": action}
    if scene_name:
        args["scene_name"] = scene_name
    return bridge.call_tool("manage_scene", args)


def unity_editor(bridge: UnityBridge, action: str) -> str:
    """Control Editor — play, pause, stop, refresh, build."""
    return bridge.call_tool("manage_editor", {"action": action})


def unity_find(bridge: UnityBridge, search_type: str,
               value: str, scene_only: bool = True) -> str:
    """Find objects — by name, tag, component, layer."""
    args = {"search_type": search_type, "value": value, "scene_only": scene_only}
    return bridge.call_tool("manage_find", args)


def unity_material(bridge: UnityBridge, action: str, name: str,
                   shader: str = None, properties: str = None) -> str:
    """Manage Materials — create, modify, assign."""
    args = {"action": action, "name": name}
    if shader:
        args["shader"] = shader
    if properties:
        args["properties"] = properties
    return bridge.call_tool("manage_material", args)


def unity_script(bridge: UnityBridge, action: str, name: str,
                 gameobject: str = None, template: str = None,
                 namespace: str = None) -> str:
    """Manage Scripts — create, attach, detach."""
    args = {"action": action, "name": name}
    if gameobject:
        args["gameobject"] = gameobject
    if template:
        args["template"] = template
    if namespace:
        args["namespace"] = namespace
    return bridge.call_tool("manage_script", args)


def unity_asset(bridge: UnityBridge, action: str,
                path: str = None, asset_type: str = None) -> str:
    """Manage Assets — import, find, refresh database."""
    args = {"action": action}
    if path:
        args["path"] = path
    if asset_type:
        args["asset_type"] = asset_type
    return bridge.call_tool("manage_asset", args)


def unity_console(bridge: UnityBridge, action: str,
                  count: int = None) -> str:
    """Manage Console — get logs, clear, filter errors."""
    args = {"action": action}
    if count is not None:
        args["count"] = count
    return bridge.call_tool("manage_console", args)


def unity_prefab(bridge: UnityBridge, action: str, name: str,
                 path: str = None, position: str = None) -> str:
    """Manage Prefabs — create, instantiate, update."""
    args = {"action": action, "name": name}
    if path:
        args["path"] = path
    if position:
        args["position"] = position
    return bridge.call_tool("manage_prefab", args)


# === Claude API Tool Schemas ===
# Only injected into Claude's tool list when the MCP server is reachable.

UNITY_TOOLS_SCHEMA = [
    {
        "name": "unity_gameobject",
        "description": "Manage Unity GameObjects. Actions: create, delete, rename, move, set_active. Position/rotation/scale as 'x,y,z' strings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: create, delete, rename, move, set_active",
                    "enum": ["create", "delete", "rename", "move", "set_active"]
                },
                "name": {
                    "type": "string",
                    "description": "GameObject name"
                },
                "parent": {
                    "type": "string",
                    "description": "Parent GameObject name (for create/move)"
                },
                "position": {
                    "type": "string",
                    "description": "Position as 'x,y,z' (e.g., '0,1,0')"
                },
                "rotation": {
                    "type": "string",
                    "description": "Rotation as 'x,y,z' euler angles"
                },
                "scale": {
                    "type": "string",
                    "description": "Scale as 'x,y,z' (e.g., '1,1,1')"
                }
            },
            "required": ["action", "name"]
        }
    },
    {
        "name": "unity_component",
        "description": "Manage Unity Components on GameObjects. Actions: add, remove, get, modify. Use component_type for the full type name (e.g., 'Rigidbody', 'BoxCollider').",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: add, remove, get, modify",
                    "enum": ["add", "remove", "get", "modify"]
                },
                "gameobject": {
                    "type": "string",
                    "description": "Target GameObject name"
                },
                "component_type": {
                    "type": "string",
                    "description": "Component type (e.g., 'Rigidbody', 'MeshRenderer')"
                },
                "properties": {
                    "type": "string",
                    "description": "JSON string of properties to set (for modify)"
                }
            },
            "required": ["action", "gameobject"]
        }
    },
    {
        "name": "unity_scene",
        "description": "Manage Unity Scenes. Actions: load, save, new, get_hierarchy. get_hierarchy returns the full scene tree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: load, save, new, get_hierarchy",
                    "enum": ["load", "save", "new", "get_hierarchy"]
                },
                "scene_name": {
                    "type": "string",
                    "description": "Scene name (for load/new)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "unity_editor",
        "description": "Control Unity Editor playback and state. Actions: play, pause, stop, step, refresh_assets, build.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: play, pause, stop, step, refresh_assets, build",
                    "enum": ["play", "pause", "stop", "step", "refresh_assets", "build"]
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "unity_find",
        "description": "Find GameObjects in the Unity scene. Search by name, tag, component type, or layer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_type": {
                    "type": "string",
                    "description": "What to search by: name, tag, component, layer",
                    "enum": ["name", "tag", "component", "layer"]
                },
                "value": {
                    "type": "string",
                    "description": "Search value (name, tag name, component type, or layer name)"
                },
                "scene_only": {
                    "type": "boolean",
                    "description": "Only search active scene (default: true)"
                }
            },
            "required": ["search_type", "value"]
        }
    },
    {
        "name": "unity_material",
        "description": "Manage Unity Materials. Actions: create, modify, assign, get. Specify shader and properties.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: create, modify, assign, get",
                    "enum": ["create", "modify", "assign", "get"]
                },
                "name": {
                    "type": "string",
                    "description": "Material name"
                },
                "shader": {
                    "type": "string",
                    "description": "Shader name (e.g., 'Standard', 'Universal Render Pipeline/Lit')"
                },
                "properties": {
                    "type": "string",
                    "description": "JSON string of material properties to set"
                }
            },
            "required": ["action", "name"]
        }
    },
    {
        "name": "unity_script",
        "description": "Manage Unity C# scripts. Actions: create (new .cs file), attach (to GameObject), detach. Optionally specify template and namespace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: create, attach, detach",
                    "enum": ["create", "attach", "detach"]
                },
                "name": {
                    "type": "string",
                    "description": "Script name (without .cs extension)"
                },
                "gameobject": {
                    "type": "string",
                    "description": "GameObject to attach/detach (for attach/detach)"
                },
                "template": {
                    "type": "string",
                    "description": "Template: MonoBehaviour, ScriptableObject, Editor"
                },
                "namespace": {
                    "type": "string",
                    "description": "C# namespace for the script"
                }
            },
            "required": ["action", "name"]
        }
    },
    {
        "name": "unity_asset",
        "description": "Manage Unity Assets. Actions: import, find, refresh_database, get_info. Use path relative to Assets/.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: import, find, refresh_database, get_info",
                    "enum": ["import", "find", "refresh_database", "get_info"]
                },
                "path": {
                    "type": "string",
                    "description": "Asset path relative to Assets/ (e.g., 'Materials/MyMat.mat')"
                },
                "asset_type": {
                    "type": "string",
                    "description": "Asset type filter (e.g., 'Material', 'Texture2D', 'Prefab')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "unity_console",
        "description": "Read Unity console output. Actions: get_logs, get_errors, get_warnings, clear. Returns recent log entries from the Editor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: get_logs, get_errors, get_warnings, clear",
                    "enum": ["get_logs", "get_errors", "get_warnings", "clear"]
                },
                "count": {
                    "type": "integer",
                    "description": "Number of log entries to return (default: 20)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "unity_prefab",
        "description": "Manage Unity Prefabs. Actions: create (from GameObject), instantiate (into scene), update (apply overrides).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: create, instantiate, update",
                    "enum": ["create", "instantiate", "update"]
                },
                "name": {
                    "type": "string",
                    "description": "Prefab name"
                },
                "path": {
                    "type": "string",
                    "description": "Path in Assets/ for create, or prefab path for instantiate"
                },
                "position": {
                    "type": "string",
                    "description": "Spawn position as 'x,y,z' (for instantiate)"
                }
            },
            "required": ["action", "name"]
        }
    }
]
