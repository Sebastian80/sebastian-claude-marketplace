# Troubleshooting Guide

## Quick Health Check

```bash
# Check daemon and Jira connection
skills-client health

# Verify Jira credentials
jira user me
```

## Configuration

Credentials loaded from `~/.env.jira`:

### Jira Cloud
```bash
JIRA_URL=https://yourcompany.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
```

### Jira Server/Data Center
```bash
JIRA_URL=https://jira.yourcompany.com
JIRA_PERSONAL_TOKEN=your-personal-access-token
```

## Common Errors

### "Could not start daemon"

**Cause**: Daemon failed to start or port 9100 in use.

**Fix**:
1. Check if something else uses port 9100: `ss -tlnp | grep 9100`
2. Check daemon logs: `tail ~/.local/share/ai-tool-bridge/logs/daemon.log`
3. Restart daemon: `bridge restart`

### "Connection failed" / "Connection reset"

**Cause**: Network issue or ESET security software intercepting loopback.

**Fix**:
1. Daemon uses IPv6 loopback to bypass ESET - should work automatically
2. If persists, check daemon is running: `skills-client health`

### "401 Unauthorized"

**Cause**: Invalid credentials.

**Cloud Fix**:
1. Generate new API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Use email as `JIRA_USERNAME`, not display name

**Server/DC Fix**:
1. Create PAT in Jira: Profile → Personal Access Tokens
2. Use only `JIRA_PERSONAL_TOKEN`, not username/password

### "403 Forbidden"

**Cause**: Valid auth but no permission.

**Fix**:
1. Verify account has project access
2. Check if IP allowlisting blocks API access
3. Confirm API access not disabled by admin

### "Issue does not exist"

**Cause**: Wrong key or no permission.

**Fix**:
1. Verify issue key spelling and case
2. Confirm you have "Browse" permission on project
3. Check if issue was moved/deleted

### "detail: Not Found"

**Cause**: Wrong command syntax or endpoint doesn't exist.

**Fix**:
1. Check command with `jira --help`
2. Positional args become path: `jira user me` → `/jira/user/me`

## Debug Mode

```bash
# Check daemon status
bridge health

# View daemon logs
tail -f ~/.local/share/ai-tool-bridge/logs/daemon.log

# Test direct API call
curl -s "http://[::1]:9100/jira/user/me"
```

## Auth Mode Detection

The daemon auto-detects auth mode:
- If `JIRA_PERSONAL_TOKEN` set → Server/DC PAT auth
- If `JIRA_USERNAME` + `JIRA_API_TOKEN` set → Cloud basic auth
- URL containing `.atlassian.net` → Cloud mode
