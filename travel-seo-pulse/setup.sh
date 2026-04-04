#!/bin/bash
# Travel SEO Pulse — Quick Setup
# Run this once to install dependencies and create the output directory.

set -e

echo "=== Travel SEO Pulse Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.12+."
    exit 1
fi

echo "Python: $(python3 --version)"

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Create output directory
mkdir -p output

# Check for required env vars
echo ""
echo "=== Environment Variables ==="
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠  ANTHROPIC_API_KEY not set"
    echo "   Run: export ANTHROPIC_API_KEY='sk-ant-...'"
else
    echo "✓  ANTHROPIC_API_KEY is set"
fi

if [ -z "$SUBSTACK_COOKIE" ]; then
    echo "⚠  SUBSTACK_COOKIE not set"
    echo "   To get it:"
    echo "   1. Log in to substack.com in Chrome"
    echo "   2. DevTools → Application → Cookies → substack.com"
    echo "   3. Copy the value of 'substack.sid'"
    echo "   4. Run: export SUBSTACK_COOKIE='your-cookie-value'"
else
    echo "✓  SUBSTACK_COOKIE is set"
fi

if [ -z "$SUBSTACK_USER_ID" ]; then
    echo "⚠  SUBSTACK_USER_ID not set"
    echo "   To get it:"
    echo "   1. Go to your Substack dashboard"
    echo "   2. DevTools → Console → run: JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps.user?.id"
    echo "   3. Run: export SUBSTACK_USER_ID='your-user-id'"
else
    echo "✓  SUBSTACK_USER_ID is set"
fi

echo ""
echo "=== Quick Start ==="
echo "  Test feeds:     python3 main.py --dry-run"
echo "  Preview issue:  python3 main.py --preview"
echo "  Draft only:     python3 main.py --draft"
echo "  Full send:      python3 main.py"
echo ""
echo "=== n8n Setup ==="
echo "  Import n8n_workflow.json into your n8n instance."
echo "  The workflow runs daily at 6am."
echo ""
echo "Setup complete."
