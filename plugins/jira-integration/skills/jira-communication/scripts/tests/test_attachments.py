"""
Tests for attachment endpoints.

Endpoints tested:
- GET /attachments/{key} - List attachments on issue
- POST /attachment/{key} - Upload attachment (skipped - write operation)
- DELETE /attachment/{attachment_id} - Delete attachment (skipped - write operation)
"""

import pytest

from helpers import TEST_PROJECT, TEST_ISSUE, run_cli, get_data, run_cli_raw


class TestListAttachments:
    """Test /attachments/{key} endpoint."""

    def test_list_attachments_basic(self):
        """Should list attachments on an issue."""
        result = run_cli("jira", "attachments", TEST_ISSUE)
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_attachments_json_format(self):
        """Should return JSON format by default."""
        result = run_cli("jira", "attachments", TEST_ISSUE, "--format", "json")
        data = get_data(result)
        assert isinstance(data, list)

    def test_list_attachments_human_format(self):
        """Should format attachments for human reading."""
        stdout, stderr, code = run_cli_raw("jira", "attachments", TEST_ISSUE, "--format", "human")
        assert code == 0

    def test_list_attachments_ai_format(self):
        """Should format attachments for AI consumption."""
        stdout, stderr, code = run_cli_raw("jira", "attachments", TEST_ISSUE, "--format", "ai")
        assert code == 0

    def test_list_attachments_markdown_format(self):
        """Should format attachments as markdown."""
        stdout, stderr, code = run_cli_raw("jira", "attachments", TEST_ISSUE, "--format", "markdown")
        assert code == 0

    def test_list_attachments_structure(self):
        """Attachments should have expected structure if present."""
        result = run_cli("jira", "attachments", TEST_ISSUE)
        data = get_data(result)
        if len(data) > 0:
            attachment = data[0]
            # Attachments typically have: id, filename, size, mimeType, content
            assert "id" in attachment or "filename" in attachment or "self" in attachment

    def test_list_attachments_invalid_issue(self):
        """Should handle non-existent issue gracefully."""
        stdout, stderr, code = run_cli_raw("jira", "attachments", "NONEXISTENT-99999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or "detail" in stdout_lower or code != 0)


class TestAttachmentHelp:
    """Test attachment help system."""

    def test_attachments_help(self):
        """Should show help for attachments command."""
        stdout, stderr, code = run_cli_raw("jira", "attachments", "--help")
        # Should show help or at least not error
        assert code == 0 or "attachments" in stdout.lower()


class TestUploadAttachment:
    """Test /attachment/{key} POST endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_upload_attachment(self):
        """Should upload attachment to issue."""
        import base64
        content = base64.b64encode(b"test content").decode()
        result = run_cli("jira", "attachment", TEST_ISSUE,
                        "--filename", "test.txt", "--content", content)
        # Should return attachment info
        data = get_data(result)
        assert "id" in data or isinstance(data, list)


class TestDeleteAttachment:
    """Test /attachment/{attachment_id} DELETE endpoint."""

    @pytest.mark.skip(reason="Write test - run manually with --run-write-tests")
    def test_delete_attachment(self):
        """Should delete attachment by ID."""
        # Would need to know an attachment ID
        pass

    def test_delete_nonexistent_attachment(self):
        """Should handle deleting non-existent attachment."""
        stdout, stderr, code = run_cli_raw("jira", "attachment/delete", "99999999")
        stdout_lower = stdout.lower()
        assert ("not found" in stdout_lower or "error" in stdout_lower or
                "existiert nicht" in stdout_lower or code != 0)


class TestAttachmentEdgeCases:
    """Test edge cases for attachments."""

    def test_attachment_invalid_key_format(self):
        """Should handle invalid issue key format."""
        stdout, stderr, code = run_cli_raw("jira", "attachments", "invalid-key-format")
        assert ("error" in stdout.lower() or "not found" in stdout.lower() or
                "existiert nicht" in stdout.lower() or code != 0)

    def test_attachment_empty_key(self):
        """Should handle missing issue key."""
        stdout, stderr, code = run_cli_raw("jira", "attachments")
        # Should error - missing required parameter or return not found
        stdout_lower = stdout.lower()
        assert ("error" in stdout_lower or "required" in stderr.lower() or
                "not found" in stdout_lower or code != 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
