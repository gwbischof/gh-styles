#!/usr/bin/env python3
"""
Generate a style document from GitHub comments using Claude Code.
Processes comments in batches, tracks progress, and compacts when necessary.
"""

import json
import os
import sys
import subprocess
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse

class StyleDocumentGenerator:
    def __init__(self, comments_file: str, output_file: str = "gwbischof_style_document.md", 
                 progress_file: str = "progress.json", batch_size: int = 250, max_lines: int = 5000):
        self.comments_file = comments_file
        self.output_file = output_file
        self.progress_file = progress_file
        self.batch_size = batch_size
        self.max_lines = max_lines
        self.current_line = 0
        self.style_content = ""
        self.compaction_count = 0
        
    def load_progress(self) -> None:
        """Load progress from previous run."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    self.current_line = progress.get('current_line', 0)
                    self.style_content = progress.get('style_content', '')
                    self.compaction_count = progress.get('compaction_count', 0)
                    print(f"Resuming from line {self.current_line}, compactions: {self.compaction_count}")
            except Exception as e:
                print(f"Error loading progress: {e}")
                print("Starting fresh...")
    
    def save_progress(self) -> None:
        """Save current progress."""
        progress = {
            'current_line': self.current_line,
            'style_content': self.style_content,
            'compaction_count': self.compaction_count,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            print(f"Error saving progress: {e}")
    
    def get_total_lines(self) -> int:
        """Get total number of lines in comments file."""
        try:
            with open(self.comments_file, 'r') as f:
                return sum(1 for _ in f)
        except Exception as e:
            print(f"Error counting lines: {e}")
            return 0
    
    def read_comment_batch(self, start_line: int, batch_size: int) -> List[Dict[str, Any]]:
        """Read a batch of comments starting from start_line."""
        comments = []
        try:
            with open(self.comments_file, 'r') as f:
                for i, line in enumerate(f):
                    if i < start_line:
                        continue
                    if len(comments) >= batch_size:
                        break
                    try:
                        comment = json.loads(line.strip())
                        comments.append(comment)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON at line {i+1}: {e}")
                        continue
        except Exception as e:
            print(f"Error reading comments: {e}")
        return comments
    
    def call_claude(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Call Claude Code with the given prompt using stdin."""
        print(f"Calling Claude with {len(prompt)} character prompt...")
        try:
            # Create a full prompt with system instructions
            full_prompt = f"""<system>
You are a document processing assistant. Your role is to process text content and return the requested output directly without any meta-commentary, explanations, or requests for permissions. 

When asked to update or merge documents, return only the final document content. Do not include phrases like "I need permissions", "Would you like me to", or any conversational responses.

You are running in an automated script that expects only the processed content as output.
</system>

{prompt}"""
            
            cmd = ['claude']
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True)
            
            print("Sending prompt to Claude...")
            stdout, stderr = process.communicate(input=full_prompt, timeout=timeout)
            
            if process.returncode == 0:
                result = stdout.strip()
                print(f"Claude responded with {len(result)} characters")
                return result
            else:
                print(f"Claude error (return code {process.returncode}): {stderr}")
                return None
        except subprocess.TimeoutExpired:
            print(f"Claude call timed out after {timeout} seconds")
            if 'process' in locals():
                process.kill()
            return None
        except Exception as e:
            print(f"Error calling Claude: {e}")
            return None
    
    def analyze_comment_batch(self, comments: List[Dict[str, Any]]) -> Optional[str]:
        """Analyze a batch of comments for style patterns."""
        if not comments:
            return None
            
        comments_text = "\n".join([
            f"Repository: {c.get('repository', 'unknown')}\n"
            f"Date: {c.get('created_at', 'unknown')}\n"
            f"Comment: {c.get('comment_body', '')}\n"
            f"Context: Issue #{c.get('issue_number', 'N/A')} - {c.get('issue_title', 'N/A')}\n"
            "---" for c in comments
        ])
        
        prompt = f"""Analyze these GitHub comments for writing style patterns. Focus on:
1. Communication tone and approach
2. Technical language preferences
3. Problem-solving methodology
4. Feedback and collaboration style
5. Common phrases or expressions
6. Code review patterns

Extract concise style insights that would help an AI assistant write similar comments.

Comments to analyze:
{comments_text}

Provide specific, actionable style guidelines based on these examples."""
        
        return self.call_claude(prompt)
    
    def update_style_document(self, new_analysis: str) -> Optional[str]:
        """Update the existing style document with new analysis, creating a completely new improved version."""
        if not self.style_content:
            return new_analysis
            
        prompt = f"""You are a content processor updating a GitHub comment style guide. You must output the complete updated document content directly.

TASK: Return the complete updated style document content (just the content, no explanations or permission requests).

REQUIREMENTS:
1. Make the document MORE DETAILED than the existing one
2. PRESERVE all existing insights, examples, and specific details
3. ADD new insights from the new analysis to expand sections
4. EXPAND existing points with additional examples and specifics
5. The document should GROW in detail and comprehensiveness, never shrink
6. Do NOT remove or simplify existing content - only enhance and expand it

EXISTING STYLE DOCUMENT:
{self.style_content}

NEW ANALYSIS TO INTEGRATE:
{new_analysis}

OUTPUT ONLY the complete updated style document content (no meta-commentary, no permission requests, just the document content)."""
        
        return self.call_claude(prompt, timeout=120)
    
    def count_lines(self, text: str) -> int:
        """Count lines in text."""
        return len(text.split('\n')) if text else 0
    
    def compact_style_document(self) -> bool:
        """Compact the current style document to make room for more content."""
        if not self.style_content:
            return False
            
        print(f"Compacting style document (current: {self.count_lines(self.style_content)} lines)...")
        
        prompt = f"""The following style document has grown too large. Please compact it while preserving all unique insights and patterns. 

Goals:
1. Merge redundant or similar style points
2. Consolidate examples while keeping the most representative ones
3. Maintain the structure and readability
4. Preserve all unique insights and edge cases
5. Target around 3000-4000 lines to allow for continued growth

Current style document:
{self.style_content}

Please provide a compacted version that maintains all the essential style information."""
        
        compacted = self.call_claude(prompt, timeout=600)
        if compacted:
            self.style_content = compacted
            self.compaction_count += 1
            new_line_count = self.count_lines(self.style_content)
            print(f"Compaction complete. New size: {new_line_count} lines (compaction #{self.compaction_count})")
            return True
        else:
            print("Compaction failed")
            return False
    
    def save_style_document(self) -> None:
        """Save the current style document to file."""
        try:
            with open(self.output_file, 'w') as f:
                header = f"""# GitHub Comment Style Guide for gwbischof

Generated from {self.current_line} comments on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Compactions performed: {self.compaction_count}

---

"""
                f.write(header + self.style_content)
        except Exception as e:
            print(f"Error saving style document: {e}")
    
    def run(self) -> None:
        """Main processing loop."""
        print("Starting style document generation...")
        
        self.load_progress()
        total_lines = self.get_total_lines()
        print(f"Total comments to process: {total_lines}")
        print(f"Starting from line: {self.current_line}")
        
        try:
            while self.current_line < total_lines:
                batch = self.read_comment_batch(self.current_line, self.batch_size)
                if not batch:
                    break
                
                print(f"Processing batch: lines {self.current_line}-{self.current_line + len(batch)} "
                      f"({(self.current_line/total_lines)*100:.1f}%)")
                
                analysis = self.analyze_comment_batch(batch)
                if analysis:
                    print(f"Got analysis: {len(analysis)} characters")
                    if self.style_content:
                        print("Updating existing style document...")
                        original_length = len(self.style_content)
                        updated_content = self.update_style_document(analysis)
                        if updated_content and len(updated_content.strip()) > 0:
                            new_length = len(updated_content)
                            if new_length >= original_length * 0.9:  # Allow slight compression but not major shrinking
                                print(f"Update successful: {original_length} -> {new_length} characters")
                                self.style_content = updated_content
                            else:
                                print(f"Update made document too small ({original_length} -> {new_length}), appending instead...")
                                self.style_content += "\n\n" + analysis
                        else:
                            print(f"Update failed. Response: '{updated_content}'. Appending instead...")
                            self.style_content += "\n\n" + analysis
                    else:
                        print("First batch - setting initial content")
                        self.style_content = analysis
                else:
                    print("No analysis returned from batch processing")
                
                current_line_count = self.count_lines(self.style_content)
                print(f"Style document now has {current_line_count} lines")
                
                if current_line_count > self.max_lines:
                    if not self.compact_style_document():
                        print("Failed to compact. Continuing anyway...")
                
                self.current_line += len(batch)
                self.save_progress()
                self.save_style_document()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nInterrupted by user. Saving progress...")
            self.save_progress()
            self.save_style_document()
            sys.exit(0)
        except Exception as e:
            print(f"Error during processing: {e}")
            self.save_progress()
            self.save_style_document()
            sys.exit(1)
        
        print(f"Processing complete! Final style document: {self.output_file}")
        print(f"Final size: {self.count_lines(self.style_content)} lines")
        print(f"Compactions performed: {self.compaction_count}")

def main():
    parser = argparse.ArgumentParser(description='Generate style document from GitHub comments')
    parser.add_argument('--comments', default='gwbischof_comments.json', 
                        help='Path to comments JSON file')
    parser.add_argument('--output', default='gwbischof_style_document.md',
                        help='Output style document file')
    parser.add_argument('--batch-size', type=int, default=250,
                        help='Number of comments to process per batch')
    parser.add_argument('--max-lines', type=int, default=5000,
                        help='Maximum lines before compaction')
    
    args = parser.parse_args()
    
    generator = StyleDocumentGenerator(
        comments_file=args.comments,
        output_file=args.output,
        batch_size=args.batch_size,
        max_lines=args.max_lines
    )
    
    generator.run()

if __name__ == "__main__":
    main()