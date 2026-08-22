import os
from config.settings import _load_dotenv
from agent.tools.base import ToolContext, ToolRegistry
from integrations.github_tool import register_github_tools
from integrations.vercel_tool import register_vercel_tools

_load_dotenv()
print("GITHUB_TOKEN:", "Set" if os.environ.get("GITHUB_TOKEN") else "Missing")
print("VERCEL_TOKEN:", "Set" if os.environ.get("VERCEL_TOKEN") else "Missing")

reg = ToolRegistry()
register_github_tools(reg)
register_vercel_tools(reg)

ctx = ToolContext(run_id="test", project="kalki")

print("\n--- GITHUB TEST ---")
gh_tool = reg.get("github_get_repo")
res = gh_tool.invoke({"repo": "Satvik2813/Kalki"}, ctx)
print("Error:", res.error)
if res.output:
    print("Repo Name:", res.output.get("full_name"))

print("\n--- VERCEL TEST ---")
# Let's test a safe Vercel operation, e.g. vercel_status if we had a deployment ID, 
# but without one it might just error with missing ID. That's fine, it proves the tool loads.
# Let's just do a manual API call since vercel_logs requires a deployment_id.
from integrations.vercel_tool import _vercel_call, _token
try:
    token = _token()
    if token:
        # Vercel API /v9/projects
        data = _vercel_call("GET", "/v9/projects/prj_5V6rOMifLMdZLqbiZFqLnX3EUnsA", token)
        print("Vercel API Success!")
        print("Project Name:", data.get("name"))
except Exception as e:
    print("Vercel error:", e)
