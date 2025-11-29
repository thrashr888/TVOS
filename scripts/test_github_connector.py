#!/usr/bin/env python3
"""
Test script for GitHub connector implementation.
Tests basic functionality without requiring real GitHub credentials.
"""

import os
import sys

# Set test environment variables BEFORE importing
os.environ["GITHUB_CLIENT_ID"] = "test_client_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_client_secret"

from tvos.connectors import GitHubConnector
from datetime import datetime


def test_requirement_2_1():
    """Test Requirement 2.1: OAuth Authentication Flow"""
    print("\n=== Testing Requirement 2.1: OAuth Authentication Flow ===")
    
    connector = GitHubConnector()
    
    # Test OAuth URL generation
    auth_url = connector.get_auth_url(state="test_state_123")
    
    print(f"Generated OAuth URL: {auth_url}")
    
    # Verify URL contains required parameters
    assert "client_id=test_client_id" in auth_url, "URL should contain client_id"
    assert "redirect_uri=" in auth_url, "URL should contain redirect_uri"
    assert "scope=" in auth_url, "URL should contain scope"
    assert "state=test_state_123" in auth_url, "URL should contain state parameter"
    assert "github.com/login/oauth/authorize" in auth_url, "URL should point to GitHub OAuth"
    
    print("✓ OAuth URL generation works correctly")
    print("✓ Requirement 2.1 validated")


def test_connector_properties():
    """Test basic connector properties"""
    print("\n=== Testing Connector Properties ===")
    
    connector = GitHubConnector()
    
    # Test name and display_name
    assert connector.name == "github", f"Expected name 'github', got '{connector.name}'"
    assert connector.display_name == "GitHub", f"Expected display_name 'GitHub', got '{connector.display_name}'"
    
    print(f"Connector name: {connector.name}")
    print(f"Connector display name: {connector.display_name}")
    print("✓ Connector properties are correct")


def test_rate_limit_info():
    """Test rate limit information"""
    print("\n=== Testing Rate Limit Info ===")
    
    connector = GitHubConnector()
    
    rate_limit_info = connector.get_rate_limit_info()
    
    print(f"Rate limit info: {rate_limit_info}")
    
    assert "requests_per_hour" in rate_limit_info, "Should have requests_per_hour"
    assert rate_limit_info["requests_per_hour"] == 5000, "Should be 5000 requests per hour for authenticated"
    
    print("✓ Rate limit info is correct")


def test_event_transformation():
    """Test event transformation for different GitHub event types"""
    print("\n=== Testing Event Transformation ===")
    
    connector = GitHubConnector()
    
    # Test commit transformation
    print("\nTesting commit transformation...")
    commit_event = {
        "type": "commit",
        "repository": "owner/repo",
        "sha": "abc123def456",
        "message": "Fix bug in authentication",
        "author": "John Doe",
        "author_email": "john@example.com",
        "timestamp": "2024-01-15T10:30:00Z",
        "url": "https://github.com/owner/repo/commit/abc123",
    }
    
    event_payload = connector.transform_event(commit_event)
    
    assert event_payload.event_id == "github_commit_abc123def456", "Event ID should match commit SHA"
    assert event_payload.source == "github", "Source should be 'github'"
    assert "Fix bug in authentication" in event_payload.text_payload, "Text should contain commit message"
    assert "John Doe" in event_payload.text_payload, "Text should contain author"
    assert event_payload.metadata["type"] == "commit", "Metadata should indicate commit type"
    assert event_payload.metadata["repository"] == "owner/repo", "Metadata should contain repository"
    
    print("✓ Commit transformation works correctly")
    
    # Test pull request transformation
    print("\nTesting pull request transformation...")
    pr_event = {
        "type": "pull_request",
        "repository": "owner/repo",
        "number": 42,
        "title": "Add new feature",
        "state": "open",
        "author": "jane_dev",
        "timestamp": "2024-01-15T11:00:00Z",
        "created_at": "2024-01-14T09:00:00Z",
        "url": "https://github.com/owner/repo/pull/42",
        "body": "This PR adds a new feature for users",
    }
    
    event_payload = connector.transform_event(pr_event)
    
    assert event_payload.event_id == "github_pr_owner_repo_42", "Event ID should match PR number"
    assert event_payload.source == "github", "Source should be 'github'"
    assert "Add new feature" in event_payload.text_payload, "Text should contain PR title"
    assert "jane_dev" in event_payload.text_payload, "Text should contain author"
    assert event_payload.metadata["type"] == "pull_request", "Metadata should indicate PR type"
    assert event_payload.metadata["number"] == "42", "Metadata should contain PR number"
    assert event_payload.metadata["state"] == "open", "Metadata should contain state"
    
    print("✓ Pull request transformation works correctly")
    
    # Test issue transformation
    print("\nTesting issue transformation...")
    issue_event = {
        "type": "issue",
        "repository": "owner/repo",
        "number": 123,
        "title": "Bug: Login fails",
        "state": "open",
        "author": "bug_reporter",
        "timestamp": "2024-01-15T12:00:00Z",
        "created_at": "2024-01-15T11:30:00Z",
        "url": "https://github.com/owner/repo/issues/123",
        "body": "When I try to login, I get an error",
        "labels": ["bug", "priority-high"],
    }
    
    event_payload = connector.transform_event(issue_event)
    
    assert event_payload.event_id == "github_issue_owner_repo_123", "Event ID should match issue number"
    assert event_payload.source == "github", "Source should be 'github'"
    assert "Bug: Login fails" in event_payload.text_payload, "Text should contain issue title"
    assert "bug_reporter" in event_payload.text_payload, "Text should contain author"
    assert event_payload.metadata["type"] == "issue", "Metadata should indicate issue type"
    assert event_payload.metadata["number"] == "123", "Metadata should contain issue number"
    assert "bug" in event_payload.metadata["labels"], "Metadata should contain labels"
    
    print("✓ Issue transformation works correctly")
    print("✓ Requirement 2.4 validated")


def test_handle_rate_limit():
    """Test rate limit handling"""
    print("\n=== Testing Rate Limit Handling ===")
    
    connector = GitHubConnector()
    
    # Test with retry_after header
    delay = connector.handle_rate_limit(retry_after=120)
    assert delay == 120, "Should use retry_after value when provided"
    print(f"✓ Uses retry_after value: {delay}s")
    
    # Test without retry_after (default exponential backoff)
    delay = connector.handle_rate_limit()
    assert delay == 60, "Should use default 60s backoff"
    print(f"✓ Uses default backoff: {delay}s")
    
    print("✓ Rate limit handling works correctly")
    print("✓ Requirement 2.5 validated")


def main():
    """Run all tests"""
    print("=" * 60)
    print("GitHub Connector Implementation Tests")
    print("=" * 60)
    
    try:
        test_connector_properties()
        test_requirement_2_1()
        test_rate_limit_info()
        test_event_transformation()
        test_handle_rate_limit()
        
        print("\n" + "=" * 60)
        print("✓ All GitHub connector tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
