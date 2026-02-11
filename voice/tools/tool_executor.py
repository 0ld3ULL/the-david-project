"""
Tool Executor for DEVA - Orchestrates tool calls from Claude API.

Handles the tool use loop:
1. Send message to Claude with tools
2. If Claude returns tool_use, execute the tool
3. Send tool result back to Claude
4. Repeat until Claude returns text response
"""

import os
import re
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

import anthropic

from voice.tools.file_tools import FileTools, FILE_TOOLS_SCHEMA
from voice.tools.command_tools import CommandTools, COMMAND_TOOLS_SCHEMA
from voice.tools.unity_tools import (
    UnityBridge, UnityBridgeConfig, UNITY_TOOLS_SCHEMA,
    unity_gameobject, unity_component, unity_scene, unity_editor,
    unity_find, unity_material, unity_script, unity_asset,
    unity_console, unity_prefab,
)


@dataclass
class ToolExecutorConfig:
    """Configuration for tool executor."""
    allowed_roots: List[str] = None  # Directories DEVA can access
    backup_dir: str = None  # Where to store file backups
    command_timeout: int = 60  # Command timeout in seconds
    max_tool_calls: int = 10  # Max tool calls per request (prevent infinite loops)
    require_confirmation: bool = False  # Require user confirmation for edits


class ToolExecutor:
    """
    Executes tools for DEVA.

    Manages the conversation loop with Claude API,
    executing tools as requested and returning results.
    """

    def __init__(self, config: ToolExecutorConfig = None):
        """
        Initialize tool executor.

        Args:
            config: Configuration options
        """
        self.config = config or ToolExecutorConfig()

        # Initialize tools
        self.file_tools = FileTools(
            allowed_roots=self.config.allowed_roots,
            backup_dir=self.config.backup_dir
        )
        self.command_tools = CommandTools(
            allowed_directories=self.config.allowed_roots,
            timeout=self.config.command_timeout
        )

        # Unity MCP bridge (graceful — only active when MCP server reachable)
        self.unity_bridge = UnityBridge()

        # Build tool registry
        self.tools = self._build_tool_registry()
        self.tool_schemas = FILE_TOOLS_SCHEMA + COMMAND_TOOLS_SCHEMA

        # Confirmation callback (set by caller if needed)
        self.confirm_callback: Optional[Callable[[str], bool]] = None

        # Execution history for this session
        self.execution_history = []

    def _build_tool_registry(self) -> Dict[str, Callable]:
        """Build mapping of tool names to functions."""
        registry = {
            # File tools
            "read_file": self._exec_read_file,
            "write_file": self._exec_write_file,
            "edit_file": self._exec_edit_file,
            "list_files": self._exec_list_files,
            "search_code": self._exec_search_code,
            "get_file_info": self._exec_get_file_info,
            # Command tools
            "run_command": self._exec_run_command,
            "git_status": self._exec_git_status,
            "git_diff": self._exec_git_diff,
            # Unity tools (MCP bridge)
            "unity_gameobject": self._exec_unity_gameobject,
            "unity_component": self._exec_unity_component,
            "unity_scene": self._exec_unity_scene,
            "unity_editor": self._exec_unity_editor,
            "unity_find": self._exec_unity_find,
            "unity_material": self._exec_unity_material,
            "unity_script": self._exec_unity_script,
            "unity_asset": self._exec_unity_asset,
            "unity_console": self._exec_unity_console,
            "unity_prefab": self._exec_unity_prefab,
        }
        return registry

    # === Tool Execution Wrappers ===

    def _exec_read_file(self, file_path: str, limit: int = None) -> str:
        result = self.file_tools.read_file(file_path, limit)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    def _exec_write_file(self, file_path: str, content: str) -> str:
        if self.config.require_confirmation and self.confirm_callback:
            if not self.confirm_callback(f"Write to {file_path}?"):
                return "Operation cancelled by user"

        result = self.file_tools.write_file(file_path, content)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    def _exec_edit_file(self, file_path: str, old_string: str,
                        new_string: str, replace_all: bool = False) -> str:
        if self.config.require_confirmation and self.confirm_callback:
            preview = f"Edit {file_path}:\n- Remove: {old_string[:100]}...\n+ Add: {new_string[:100]}..."
            if not self.confirm_callback(preview):
                return "Operation cancelled by user"

        result = self.file_tools.edit_file(file_path, old_string, new_string, replace_all)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    def _exec_list_files(self, directory: str, pattern: str = "*",
                         recursive: bool = True) -> str:
        result = self.file_tools.list_files(directory, pattern, recursive)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    def _exec_search_code(self, directory: str, pattern: str,
                          file_pattern: str = "*.cs",
                          context_lines: int = 2) -> str:
        result = self.file_tools.search_code(directory, pattern, file_pattern, context_lines)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    def _exec_get_file_info(self, file_path: str) -> str:
        result = self.file_tools.get_file_info(file_path)
        if result.success:
            return result.output
        return f"Error: {result.error}"

    def _exec_run_command(self, command: str, working_dir: str = None,
                          timeout: int = None) -> str:
        result = self.command_tools.run(command, working_dir, timeout)
        if result.success:
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            return output or "(no output)"
        return f"Error (code {result.return_code}): {result.error or result.stderr}"

    def _exec_git_status(self, repo_path: str) -> str:
        result = self.command_tools.git_status(repo_path)
        if result.success:
            return result.stdout or "(clean working tree)"
        return f"Error: {result.error or result.stderr}"

    def _exec_git_diff(self, repo_path: str, file_path: str = None) -> str:
        result = self.command_tools.git_diff(repo_path, file_path)
        if result.success:
            return result.stdout or "(no changes)"
        return f"Error: {result.error or result.stderr}"

    # === Unity Tool Wrappers ===

    def _exec_unity_gameobject(self, action: str, name: str, **kwargs) -> str:
        return unity_gameobject(self.unity_bridge, action, name, **kwargs)

    def _exec_unity_component(self, action: str, gameobject: str, **kwargs) -> str:
        return unity_component(self.unity_bridge, action, gameobject, **kwargs)

    def _exec_unity_scene(self, action: str, **kwargs) -> str:
        return unity_scene(self.unity_bridge, action, **kwargs)

    def _exec_unity_editor(self, action: str) -> str:
        return unity_editor(self.unity_bridge, action)

    def _exec_unity_find(self, search_type: str, value: str, scene_only: bool = True) -> str:
        return unity_find(self.unity_bridge, search_type, value, scene_only)

    def _exec_unity_material(self, action: str, name: str, **kwargs) -> str:
        return unity_material(self.unity_bridge, action, name, **kwargs)

    def _exec_unity_script(self, action: str, name: str, **kwargs) -> str:
        return unity_script(self.unity_bridge, action, name, **kwargs)

    def _exec_unity_asset(self, action: str, **kwargs) -> str:
        return unity_asset(self.unity_bridge, action, **kwargs)

    def _exec_unity_console(self, action: str, count: int = None) -> str:
        return unity_console(self.unity_bridge, action, count)

    def _exec_unity_prefab(self, action: str, name: str, **kwargs) -> str:
        return unity_prefab(self.unity_bridge, action, name, **kwargs)

    # === Main Execution ===

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a single tool call.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result as string
        """
        if tool_name not in self.tools:
            return f"Error: Unknown tool '{tool_name}'"

        try:
            # Get the tool function
            tool_func = self.tools[tool_name]

            # Execute with provided inputs
            result = tool_func(**tool_input)

            # Log execution
            self.execution_history.append({
                "tool": tool_name,
                "input": tool_input,
                "result": result[:500] if len(result) > 500 else result,
                "success": not result.startswith("Error")
            })

            return result

        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            self.execution_history.append({
                "tool": tool_name,
                "input": tool_input,
                "result": error_msg,
                "success": False
            })
            return error_msg

    def run_with_tools(
        self,
        client: anthropic.Anthropic,
        messages: List[Dict],
        system_prompt: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096
    ) -> tuple[str, List[Dict]]:
        """
        Run a conversation with Claude using tools.

        Handles the tool use loop automatically.

        Args:
            client: Anthropic client
            messages: Conversation messages
            system_prompt: System prompt for DEVA
            model: Model to use
            max_tokens: Max response tokens

        Returns:
            Tuple of (final_response_text, updated_messages)
        """
        tool_calls = 0

        # Conditionally inject Unity tools when MCP server is reachable
        active_schemas = list(self.tool_schemas)
        if self.unity_bridge.is_connected:
            active_schemas += UNITY_TOOLS_SCHEMA

        while tool_calls < self.config.max_tool_calls:
            # Call Claude with tools
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                tools=active_schemas,
                messages=messages
            )

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude is done - extract text response
                text_parts = [
                    block.text for block in response.content
                    if hasattr(block, 'text')
                ]
                return " ".join(text_parts), messages

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                tool_calls += 1

                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Show any thinking text Claude included alongside tool calls
                for block in response.content:
                    if hasattr(block, 'text') and block.text:
                        # Strip [SAY] tags for console - this is internal narration
                        clean = block.text.replace("[SAY]", "").replace("[/SAY]", "").strip()
                        if clean:
                            print(f"  [Thinking] {clean}")

                # Execute each tool call
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  [Tool] {block.name}({json.dumps(block.input)[:100]}...)")

                        result = self.execute_tool(block.name, block.input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            else:
                # Unknown stop reason
                return f"Unexpected stop reason: {response.stop_reason}", messages

        # Hit max tool calls
        return "I've reached the maximum number of tool operations for this request. Let me summarize what I've done so far.", messages

    def get_execution_summary(self) -> str:
        """Get a summary of tool executions in this session."""
        if not self.execution_history:
            return "No tools executed yet"

        lines = [f"Tool executions ({len(self.execution_history)}):"]
        for exec in self.execution_history[-10:]:  # Last 10
            status = "✓" if exec["success"] else "✗"
            lines.append(f"  {status} {exec['tool']}")

        return "\n".join(lines)

    def clear_history(self):
        """Clear execution history."""
        self.execution_history = []


# === Console Log Watcher ===

class ConsoleLogWatcher:
    """
    Watches Unity console log for errors and output.

    Supports:
    - Unity Editor log (Editor.log)
    - Project console log (console_log.txt)
    - Production build logs (Player.log)
    - Epic Games launcher builds
    - Custom log paths
    """

    # Common Unity log locations
    LOG_TEMPLATES = {
        "editor": r"%LOCALAPPDATA%\Unity\Editor\Editor.log",
        "player_log": r"%USERPROFILE%\AppData\LocalLow\{company}\{product}\Player.log",
        "output_log": r"%USERPROFILE%\AppData\LocalLow\{company}\{product}\output_log.txt",
    }

    def __init__(self, log_paths: List[str] = None):
        """
        Initialize log watcher.

        Args:
            log_paths: Paths to watch for changes
        """
        self.log_paths = log_paths or []
        self.last_positions = {}  # Track file positions
        self.error_patterns = [
            r"error",
            r"exception",
            r"failed",
            r"nullreferenceexception",
            r"missingreferenceexception",
            r"argumentexception",
            r"indexoutofrangeexception",
            r"keynotfoundexception",
            r"invalidoperationexception",
            r"stacktrace",
        ]

        # Initialize positions
        for path in self.log_paths:
            if os.path.exists(path):
                self.last_positions[path] = os.path.getsize(path)
            else:
                self.last_positions[path] = 0

    def add_log_path(self, path: str):
        """Add a log path to watch."""
        if path not in self.log_paths:
            self.log_paths.append(path)
            if os.path.exists(path):
                self.last_positions[path] = os.path.getsize(path)
            else:
                self.last_positions[path] = 0

    def check_for_new_content(self) -> Dict[str, str]:
        """
        Check all watched logs for new content.

        Returns:
            Dict mapping log path to new content
        """
        new_content = {}

        for path in self.log_paths:
            if not os.path.exists(path):
                continue

            current_size = os.path.getsize(path)
            last_pos = self.last_positions.get(path, 0)

            if current_size > last_pos:
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        content = f.read()
                        if content.strip():
                            new_content[path] = content
                    self.last_positions[path] = current_size
                except Exception:
                    pass

        return new_content

    def get_recent_errors(self, log_path: str, count: int = 10) -> List[str]:
        """
        Get recent error lines from a log.

        Args:
            log_path: Path to the log file
            count: Number of error lines to return

        Returns:
            List of error lines
        """
        if not os.path.exists(log_path):
            return []

        errors = []
        error_keywords = ["error", "exception", "failed", "null", "missing"]

        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in error_keywords):
                        errors.append(line.strip())

            return errors[-count:]  # Return last N errors

        except Exception:
            return []

    def get_summary(self) -> str:
        """Get a summary of watched logs."""
        lines = ["Watching logs:"]
        for path in self.log_paths:
            exists = "✓" if os.path.exists(path) else "✗"
            lines.append(f"  {exists} {path}")
        return "\n".join(lines)

    def scan_for_production_logs(self, company_name: str = None, product_name: str = None) -> List[str]:
        """
        Scan for production build logs in common locations.

        Args:
            company_name: Optional company name to filter
            product_name: Optional product name to filter

        Returns:
            List of found log paths
        """
        found_logs = []
        locallow = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow")

        if not os.path.exists(locallow):
            return found_logs

        # Scan all company/product folders
        for company in os.listdir(locallow):
            company_path = os.path.join(locallow, company)
            if not os.path.isdir(company_path):
                continue

            if company_name and company_name.lower() not in company.lower():
                continue

            for product in os.listdir(company_path):
                product_path = os.path.join(company_path, product)
                if not os.path.isdir(product_path):
                    continue

                if product_name and product_name.lower() not in product.lower():
                    continue

                # Check for Player.log and output_log.txt
                for log_name in ["Player.log", "output_log.txt"]:
                    log_path = os.path.join(product_path, log_name)
                    if os.path.exists(log_path):
                        found_logs.append(log_path)

        return found_logs

    def auto_discover_logs(self, project_path: str = None) -> int:
        """
        Auto-discover and add relevant log files.

        Args:
            project_path: Optional project path to help identify the game

        Returns:
            Number of logs added
        """
        added = 0

        # Always add editor log
        editor_log = os.path.expandvars(self.LOG_TEMPLATES["editor"])
        if editor_log not in self.log_paths:
            self.add_log_path(editor_log)
            added += 1

        # If we have a project path, try to find matching production logs
        if project_path:
            # Extract likely company/product from path
            path_parts = project_path.replace("\\", "/").split("/")
            # Look for company-like names in path
            for part in path_parts:
                if part and not part.endswith(":"):
                    prod_logs = self.scan_for_production_logs(company_name=None, product_name=part)
                    for log in prod_logs:
                        if log not in self.log_paths:
                            self.add_log_path(log)
                            added += 1

        # Scan for all production logs if nothing specific found
        if added <= 1:
            all_logs = self.scan_for_production_logs()
            for log in all_logs[:5]:  # Limit to 5 most recent
                if log not in self.log_paths:
                    self.add_log_path(log)
                    added += 1

        return added

    def get_errors_summary(self, max_errors: int = 10) -> str:
        """
        Get a summary of recent errors across all watched logs.

        Args:
            max_errors: Maximum number of errors to return

        Returns:
            Formatted error summary
        """
        import re

        all_errors = []

        for path in self.log_paths:
            if not os.path.exists(path):
                continue

            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()

                log_name = os.path.basename(path)
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(re.search(pattern, line_lower) for pattern in self.error_patterns):
                        # Get some context
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 3)
                        context = "".join(lines[context_start:context_end])

                        all_errors.append({
                            "log": log_name,
                            "line": i + 1,
                            "context": context.strip()
                        })

            except Exception:
                continue

        if not all_errors:
            return "No errors found in watched logs."

        # Return most recent errors
        recent = all_errors[-max_errors:]
        lines = [f"Found {len(all_errors)} errors, showing last {len(recent)}:"]
        for err in recent:
            lines.append(f"\n[{err['log']}:{err['line']}]")
            lines.append(err['context'][:300])

        return "\n".join(lines)
