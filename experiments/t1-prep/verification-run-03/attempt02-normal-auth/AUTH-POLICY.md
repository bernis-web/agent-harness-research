# Attempt02 authentication policy

User explicitly requested a normal authenticated client invocation. This attempt does not use --bare, does not change HOME/USERPROFILE/CLAUDE_CONFIG_DIR, and does not inspect or copy any authentication file. --setting-sources user preserves client-side user routing/auth settings while excluding project/local settings. --safe-mode local help explicitly states that auth/model selection work normally while customizations are disabled. Tools are empty, MCP is strict/empty, hooks explicitly disabled, no session persistence and no browser integration. No login, configuration edit, credential bridge or key extraction is used.

Attempt01 remains unchanged and only demonstrates failure of the intentionally isolated bare invocation, not failure of ordinary authentication.
