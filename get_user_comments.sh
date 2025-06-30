#!/bin/bash

INCLUDE_PRIVATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --include-private)
            INCLUDE_PRIVATE=true
            shift
            ;;
        -*)
            echo "Unknown option $1"
            echo "Usage: $0 <username> [--include-private]"
            echo "  --include-private  Include comments from private repositories"
            echo "Example: $0 octocat"
            echo "Example: $0 octocat --include-private"
            exit 1
            ;;
        *)
            USERNAME="$1"
            shift
            ;;
    esac
done

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <username> [--include-private]"
    echo "  --include-private  Include comments from private repositories"
    echo "Example: $0 octocat"
    echo "Example: $0 octocat --include-private"
    exit 1
fi

OUTPUT_FILE="${USERNAME}_comments.json"

echo "Fetching all comments for user: $USERNAME"
if [ "$INCLUDE_PRIVATE" = true ]; then
    echo "Including comments from private repositories"
else
    echo "Only including comments from public repositories"
fi
echo "Output will be saved to: $OUTPUT_FILE"
echo "========================================="

echo "Starting API request..."
echo "Fetching comments (this may take a while for users with many comments)..."

# Initialize output file
> "$OUTPUT_FILE"

gh api graphql -f query='
query($username: String!, $cursor: String) {
  user(login: $username) {
    issueComments(first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        body
        createdAt
        url
        issue {
          title
          number
          body
          state
          author {
            login
          }
          repository {
            name
            owner {
              login
            }
            isPrivate
          }
        }
      }
    }
  }
}' -f username="$USERNAME" --paginate --jq '.data.user.issueComments.nodes[] | '"$(if [ "$INCLUDE_PRIVATE" = true ]; then echo ""; else echo "select(.issue.repository.isPrivate == false) | "; fi)"'{
  comment_id: .id,
  created_at: .createdAt,
  url: .url,
  repository: (.issue.repository.owner.login + "/" + .issue.repository.name),
  issue_number: .issue.number,
  issue_title: .issue.title,
  issue_body: .issue.body,
  issue_state: .issue.state,
  issue_author: .issue.author.login,
  comment_body: .body
}' >> "$OUTPUT_FILE" 2>&1 &

# Show progress while the request is running
PID=$!
echo "Request started (PID: $PID)..."
while kill -0 $PID 2>/dev/null; do
    if [ -f "$OUTPUT_FILE" ]; then
        CURRENT_COUNT=$(wc -l < "$OUTPUT_FILE" 2>/dev/null | tr -d ' ')
        echo "Progress: $CURRENT_COUNT comments fetched so far..."
    fi
    sleep 5
done

# Wait for the process to complete
wait $PID

if [ $? -eq 0 ]; then
    COMMENT_COUNT=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "✓ Success! Fetched $COMMENT_COUNT comments"
    echo "Comments saved to: $OUTPUT_FILE"
else
    echo "✗ Error occurred. Check $OUTPUT_FILE for details"
    exit 1
fi
