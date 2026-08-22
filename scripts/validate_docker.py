import os
import sys
from sandbox.docker_sandbox import SandboxExecTool
from agent.tools.base import ToolContext
import time

def run_test():
    tool = SandboxExecTool()
    ctx = ToolContext(workspace_root=os.path.abspath(os.getcwd()))
    
    print("--- 1. Testing SUCCESS command ---")
    res1 = tool.run({"command": "echo KALKI_DOCKER_OK && cat /etc/os-release | grep PRETTY_NAME"}, ctx)
    print("TOOL RESULT 1 DICT:", vars(res1))
    
    print("\n--- 2. Testing FAILURE command ---")
    res2 = tool.run({"command": "ls /nonexistent_dir"}, ctx)
    print("TOOL RESULT 2 DICT:", vars(res2))
    
    print("\n--- 3. Testing ISOLATION ---")
    res3 = tool.run({"command": "ls -l /workspace/.env && ls -l /workspace/.."}, ctx)
    print("TOOL RESULT 3 DICT:", vars(res3))

if __name__ == "__main__":
    run_test()
