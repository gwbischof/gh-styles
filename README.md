# GitHub Comment Style Analyzer

Analyzes your GitHub comments using Claude Code to generate a style document for AI assistants.

## Setup

1. Install dependencies: `pixi install`
2. Authenticate: `gh auth login` and `claude auth`

## Usage

**Collect comments:**
```bash
./get_user_comments.sh username                # Public only
./get_user_comments.sh username --include-private  # Include private
```

**Generate style document:**
```bash
pixi run generate-small    # Test with small batches
pixi run generate          # Full processing
pixi run resume           # Resume if interrupted
pixi run status           # Check progress
pixi run clean            # Start fresh
```

## How it works

1. Fetches GitHub comments via GraphQL API
2. Processes in batches using Claude Code for style analysis
3. Auto-compacts when document hits 5000 lines (preserves insights)
4. Saves progress for resumability

## Troubleshooting

- Claude issues: `pixi run test-claude` or `claude auth`
- GitHub issues: `gh auth status`
- Large datasets: reduce `--batch-size` or use `generate-small`

## Output

- `{username}_comments.json` - Raw comments
- `{username}_style_document.md` - Generated style guide
- `progress.json` - Processing state