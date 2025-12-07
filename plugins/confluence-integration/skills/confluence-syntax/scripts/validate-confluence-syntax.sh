#!/bin/bash

# Confluence Wiki Markup Syntax Validator
# Checks text for common Confluence syntax errors and suggests corrections

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Counters
ERRORS=0
WARNINGS=0

# Function to print error
error() {
    echo -e "${RED}ERROR:${NC} $1"
    ((ERRORS++))
}

# Function to print warning
warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
    ((WARNINGS++))
}

# Function to print success
success() {
    echo -e "${GREEN}$1${NC}"
}

# Function to check file
validate_file() {
    local file="$1"
    echo ""
    echo "=========================================="
    echo "Validating: $file"
    echo "=========================================="

    if [ ! -f "$file" ]; then
        error "File not found: $file"
        return
    fi

    local content=$(cat "$file")
    local line_num=0

    # Check for Markdown-style headings (## instead of h2.)
    if echo "$content" | grep -qE "^##+ "; then
        error "Found Markdown-style headings (##). Use Confluence format: h2. Heading"
        echo "   Lines with issue:"
        echo "$content" | grep -nE "^##+ " | head -5
    fi

    # Check for Markdown-style bold (**text** instead of *text*)
    if echo "$content" | grep -qE "\*\*[^*]+\*\*"; then
        warning "Found Markdown-style bold (**text**). Use Confluence format: *text*"
        echo "   Examples found:"
        echo "$content" | grep -oE "\*\*[^*]+\*\*" | head -3
    fi

    # Check for Markdown-style code blocks (``` instead of {code})
    if echo "$content" | grep -qE "^\`\`\`"; then
        error "Found Markdown code blocks (\`\`\`). Use Confluence format: {code:language}"
        echo "   Lines with issue:"
        echo "$content" | grep -nE "^\`\`\`" | head -5
    fi

    # Check for Markdown-style inline code (` instead of {{)
    if echo "$content" | grep -qE "\`[^\`]+\`" && ! echo "$content" | grep -qE "{{[^}]+}}"; then
        warning "Found Markdown inline code (\`code\`). Consider Confluence format: {{code}}"
    fi

    # Check for Markdown-style links ([text](url) instead of [text|url])
    if echo "$content" | grep -qE "\[([^\]]+)\]\(([^)]+)\)"; then
        error "Found Markdown-style links ([text](url)). Use Confluence format: [text|url]"
        echo "   Examples found:"
        echo "$content" | grep -oE "\[([^\]]+)\]\(([^)]+)\)" | head -3
    fi

    # Check for headings without space after period (h2.Title instead of h2. Title)
    if echo "$content" | grep -qE "^h[1-6]\.[^ ]"; then
        error "Found headings without space after period. Use: h2. Title (not h2.Title)"
        echo "   Lines with issue:"
        echo "$content" | grep -nE "^h[1-6]\.[^ ]" | head -5
    fi

    # Check for code blocks without language specification
    if echo "$content" | grep -qE "^\{code\}[^:]" || echo "$content" | grep -qE "^\{code\}$"; then
        warning "Found {code} blocks without language. Consider: {code:java} for syntax highlighting"
    fi

    # Check for tables with incorrect header syntax (|Header| instead of ||Header||)
    if echo "$content" | grep -qE "^\|[^|]+\|$" && ! echo "$content" | grep -qE "^\|\|"; then
        warning "Potential table header without double pipes. Headers should use: ||Header||"
    fi

    # Check for unclosed {code} blocks
    local code_open=$(echo "$content" | grep -c "{code" || true)
    local code_close=$(echo "$content" | grep -c "{code}" | head -1 || true)
    # More accurate: count opening tags vs closing tags
    local code_opening=$(echo "$content" | grep -oE "\{code(:[^}]*)?\}" | wc -l || true)
    local code_closing=$(echo "$content" | grep -oE "\{code\}" | wc -l || true)

    # Check for unclosed {panel} blocks
    local panel_open=$(echo "$content" | grep -c "{panel" || true)
    local panel_close=$(echo "$content" | grep -c "{panel}" || true)

    # Check for unclosed {info}, {note}, {warning}, {tip} blocks
    for macro in info note warning tip; do
        local macro_count=$(echo "$content" | grep -o "{$macro" | wc -l || true)
        if [ $((macro_count % 2)) -ne 0 ]; then
            warning "Potential unclosed {$macro} tag (odd number of occurrences: $macro_count)"
        fi
    done

    # Check for unclosed {expand} blocks
    local expand_open=$(echo "$content" | grep -c "{expand" || true)
    local expand_close=$(echo "$content" | grep -c "{expand}" || true)
    if [ "$expand_open" -ne "$expand_close" ]; then
        warning "Mismatched {expand} tags: $expand_open opening patterns, $expand_close closing"
    fi

    # Check for unclosed {color} blocks
    local color_count=$(echo "$content" | grep -o "{color" | wc -l || true)
    if [ $((color_count % 2)) -ne 0 ]; then
        warning "Potential unclosed {color} tag (odd number of occurrences)"
    fi

    # Check for Markdown-style lists (- item instead of * item)
    if echo "$content" | grep -qE "^- [^-]"; then
        warning "Found Markdown-style bullets (- item). Confluence prefers: * item"
    fi

    # Check for Markdown-style blockquotes (> instead of {quote})
    if echo "$content" | grep -qE "^> "; then
        warning "Found Markdown-style quotes (> text). Use Confluence: {quote}...{quote} or bq. text"
        echo "   Lines with issue:"
        echo "$content" | grep -nE "^> " | head -3
    fi

    # Check for HTML that should be wiki markup
    if echo "$content" | grep -qiE "<(strong|b)>"; then
        warning "Found HTML bold tags. Use Confluence: *bold*"
    fi
    if echo "$content" | grep -qiE "<(em|i)>"; then
        warning "Found HTML italic tags. Use Confluence: _italic_"
    fi

    # Positive checks
    if echo "$content" | grep -qE "^h[1-6]\. "; then
        success "Found correctly formatted Confluence headings"
    fi

    if echo "$content" | grep -qE "{code:[a-z]+}"; then
        success "Found code blocks with language specification"
    fi

    if echo "$content" | grep -qE "\[~[a-z.]+\]"; then
        success "Found user mentions ([~username])"
    fi

    if echo "$content" | grep -qE "{(info|note|warning|tip)}"; then
        success "Found Confluence panel macros"
    fi

    if echo "$content" | grep -qE "{toc"; then
        success "Found table of contents macro"
    fi

    if echo "$content" | grep -qE "{status:"; then
        success "Found status macros"
    fi

    if echo "$content" | grep -qE "\[.+\|.+\]"; then
        success "Found correctly formatted links ([text|url])"
    fi
}

# Main script
echo "Confluence Wiki Markup Syntax Validator"
echo "========================================"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1> [file2] [file3] ..."
    echo ""
    echo "Validates Confluence wiki markup syntax in text files"
    echo ""
    echo "Example:"
    echo "  $0 page-content.txt"
    echo "  $0 templates/*.md"
    exit 1
fi

# Validate each file
for file in "$@"; do
    validate_file "$file"
done

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo "Files checked: $#"
echo -e "${RED}Errors: $ERRORS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}No errors, but $WARNINGS warnings found${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS errors found - please fix before submitting to Confluence${NC}"
    exit 1
fi
