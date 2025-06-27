#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <username>"
    echo "Example: $0 octocat"
    exit 1
fi

USERNAME="$1"
OUTPUT_FILE="${USERNAME}_comments.json"

echo "Fetching all comments for user: $USERNAME"
echo "Output will be saved to: $OUTPUT_FILE"
echo "========================================="

echo "Starting API request..."
echo "Fetching comments (this may take a while for users with many comments)..."

# Create a temp file to show progress
TEMP_FILE=$(mktemp)
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
          }
        }
      }
    }
  }
}' -f username="$USERNAME" --paginate --jq '.data.user.issueComments.nodes[] | {
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
}' > "$TEMP_FILE" 2>&1 &

# Show progress while the request is running
PID=$!
echo "Request started (PID: $PID)..."
while kill -0 $PID 2>/dev/null; do
    if [ -f "$TEMP_FILE" ]; then
        CURRENT_COUNT=$(wc -l < "$TEMP_FILE" 2>/dev/null | tr -d ' ')
        echo "Progress: $CURRENT_COUNT comments fetched so far..."
    fi
    sleep 5
done

# Move temp file to final output
mv "$TEMP_FILE" "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    COMMENT_COUNT=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "✓ Success! Fetched $COMMENT_COUNT comments"
    echo "Comments saved to: $OUTPUT_FILE"
else
    echo "✗ Error occurred. Check $OUTPUT_FILE for details"
    exit 1
fi
