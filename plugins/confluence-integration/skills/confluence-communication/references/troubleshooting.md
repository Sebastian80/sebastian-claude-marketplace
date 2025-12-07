# Troubleshooting Guide

Common issues and solutions for Confluence CLI scripts.

## Authentication Issues

### "Authentication failed" Error

**Symptoms:**
- 401 Unauthorized errors
- "Invalid credentials" messages

**Solutions:**

1. **Verify credentials in ~/.env.confluence**
   ```bash
   cat ~/.env.confluence
   ```

2. **For Confluence Cloud:**
   - `CONFLUENCE_USERNAME` must be your email address (not username)
   - `CONFLUENCE_API_TOKEN` must be generated from: https://id.atlassian.com/manage/api-tokens
   - Tokens are NOT passwords - generate a new API token

3. **For Confluence Server/DC:**
   - `CONFLUENCE_PERSONAL_TOKEN` must be a valid Personal Access Token
   - Generate at: `https://your-confluence/plugins/personalaccesstokens/usertokens.action`
   - Ensure token has not expired

4. **Check URL format:**
   ```
   # Cloud - must include .atlassian.net
   CONFLUENCE_URL=https://yourcompany.atlassian.net

   # Server - no trailing slash
   CONFLUENCE_URL=https://confluence.yourcompany.com
   ```

### "Connection refused" Error

**Solutions:**
1. Verify the URL is accessible from your network
2. Check for VPN requirements
3. Verify firewall rules
4. Test with curl: `curl -I https://your-confluence-url`

## Permission Issues

### "Page not found" but Page Exists

**Causes:**
- Your user doesn't have view permission
- Page is in a restricted space
- Wrong page ID

**Solutions:**
1. Verify you can access the page in browser
2. Check space permissions
3. Confirm page ID is correct (visible in URL)

### "Cannot create page" Error

**Causes:**
- No add permission in space
- Invalid parent page ID
- Duplicate title

**Solutions:**
1. Verify space permissions
2. Check parent page exists and is accessible
3. Use different title or check for existing page

## CQL Search Issues

### Empty Search Results

**Solutions:**
1. Verify space key is correct (case-sensitive)
2. Check content exists and is published (not draft)
3. Wait for indexing if content is new
4. Simplify query to isolate issue:
   ```bash
   # Start simple
   uv run scripts/core/confluence-search.py query "space = DEV"

   # Then add conditions
   uv run scripts/core/confluence-search.py query "space = DEV AND type = page"
   ```

### "Invalid CQL" Errors

**Common mistakes:**
- Missing quotes around values with spaces
- Wrong operator for field type
- Typo in field name

**Examples:**
```bash
# Wrong - missing quotes
space = MY SPACE

# Correct
space = "MY SPACE"

# Wrong - = for contains
title = Guide

# Correct - ~ for contains
title ~ "Guide"
```

## Script Execution Issues

### "uv: command not found"

**Solution:**
Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### "No module named 'atlassian'"

**Cause:** Dependencies not installed by uv

**Solution:**
The scripts use PEP 723 inline dependencies. Running with `uv run` should auto-install them. Try:
```bash
uv cache clean
uv run scripts/core/confluence-validate.py
```

### Flag Ordering Errors

**Symptom:** "Error: No such option"

**Cause:** Global flags placed after subcommand

**Solution:**
```bash
# Wrong
uv run scripts/core/confluence-page.py get 12345 --json

# Correct
uv run scripts/core/confluence-page.py --json get 12345
```

## Content Format Issues

### HTML Not Rendering

**Cause:** Confluence storage format uses XHTML-based markup

**Solution:**
Ensure body content is valid HTML:
```bash
# Good
--body "<p>This is a paragraph.</p>"

# Bad - missing tags
--body "This is plain text"
```

### Wiki Markup Not Converting

**Solutions:**
1. Use `confluence-convert.py` for format conversion
2. Check for nested macros that may not convert properly
3. Verify input format matches `--format` option

## Performance Issues

### Slow Searches

**Solutions:**
1. Add more specific filters (space, type)
2. Reduce `--limit` value
3. Use indexed fields when possible

### Timeout Errors

**Solutions:**
1. Check network connectivity
2. Try smaller batch sizes for bulk operations
3. Add `--timeout` option if available

## Mermaid CLI Issues

### "No usable sandbox" Error (Linux)

**Symptoms:**
```
[FATAL:zygote_host_impl_linux.cc(128)] No usable sandbox! If you are running on Ubuntu 23.10+
or another Linux distro that has disabled unprivileged user namespaces with AppArmor...
```

**Cause:** Ubuntu 23.10+ restricts Chrome sandbox via AppArmor for non-system binaries (Puppeteer's bundled Chrome).

**Solution:** Create a Puppeteer config to use system Chrome:

```bash
mkdir -p ~/.config/mermaid
cat > ~/.config/mermaid/puppeteer-config.json << 'EOF'
{
  "executablePath": "/usr/bin/google-chrome",
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
}
EOF
```

The `confluence-mermaid.py` script auto-detects `~/.config/mermaid/puppeteer-config.json`.

For direct mmdc usage, pass the config explicitly:
```bash
mmdc -i diagram.mmd -o out.svg -p ~/.config/mermaid/puppeteer-config.json
```

### "mmdc: command not found"

**Solution:** Install mermaid-cli globally:
```bash
npm install -g @mermaid-js/mermaid-cli
```

Or use the API fallback (automatic when mmdc is not installed).

### Mermaid Rendering Falls Back to API

**Cause:** mmdc not installed or failing

**Check status:**
```bash
uv run scripts/utility/confluence-mermaid.py check
```

**Note:** The mermaid.ink API fallback works without local installation but requires internet access.

## Debug Mode

For detailed error information, use `--debug`:

```bash
uv run scripts/core/confluence-page.py --debug get 12345
```

This shows full stack traces for troubleshooting.

## Getting Help

1. Check script help: `uv run scripts/core/confluence-page.py --help`
2. Validate setup: `uv run scripts/core/confluence-validate.py --verbose`
3. Test API access in browser first
4. Check Confluence admin for permission issues
