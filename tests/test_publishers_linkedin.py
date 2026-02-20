"""Tests for marketing_engine.publishers.linkedin."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from marketing_engine.enums import ContentStream, Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.linkedin import LinkedInPublisher
from marketing_engine.publishers.result import PublishResult

_PATCH_CREDS = "marketing_engine.publishers.linkedin.get_platform_credentials"
_PATCH_POST = "marketing_engine.publishers.linkedin.httpx.post"

_VALID_CREDS = {"access_token": "li-token-abc", "person_id": "person-xyz"}


def _make_post(
    content: str = "Build beautiful CLIs with Typer + Rich in Python.",
    edited_content: str | None = None,
    **kwargs,
) -> PostDraft:
    return PostDraft(
        brief_id="brief-1",
        stream=ContentStream.project_marketing,
        platform=Platform.linkedin,
        content=content,
        hashtags=["python", "cli"],
        cta_url="https://typer.tiangolo.com",
        scheduled_time=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        edited_content=edited_content,
        **kwargs,
    )


def _mock_success_response(post_urn: str = "urn:li:share:123456") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 201
    resp.headers = {"x-restli-id": post_urn}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# LinkedInPublisher.__init__ / platform
# ---------------------------------------------------------------------------


class TestLinkedInPublisherInit:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_platform_is_linkedin(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.platform == Platform.linkedin

    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_calls_get_platform_credentials(self, mock_creds):
        LinkedInPublisher()
        mock_creds.assert_called_once_with("linkedin")

    @patch(_PATCH_CREDS, return_value={})
    def test_init_with_empty_creds(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub._creds == {}


# ---------------------------------------------------------------------------
# validate_credentials
# ---------------------------------------------------------------------------


class TestLinkedInValidateCredentials:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_valid_credentials(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.validate_credentials() is True

    @patch(_PATCH_CREDS, return_value={})
    def test_missing_all_credentials(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.validate_credentials() is False

    @patch(_PATCH_CREDS, return_value={"access_token": "tok"})
    def test_missing_person_id(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.validate_credentials() is False

    @patch(_PATCH_CREDS, return_value={"person_id": "pid"})
    def test_missing_access_token(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.validate_credentials() is False

    @patch(_PATCH_CREDS, return_value={"access_token": "", "person_id": "pid"})
    def test_empty_access_token(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.validate_credentials() is False

    @patch(_PATCH_CREDS, return_value={"access_token": "tok", "person_id": ""})
    def test_empty_person_id(self, _mock_creds):
        pub = LinkedInPublisher()
        assert pub.validate_credentials() is False


# ---------------------------------------------------------------------------
# publish — success cases
# ---------------------------------------------------------------------------


class TestLinkedInPublishSuccess:
    @patch(_PATCH_POST, return_value=_mock_success_response())
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_returns_publish_result(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert isinstance(result, PublishResult)

    @patch(_PATCH_POST, return_value=_mock_success_response())
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_success_flag(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.success is True

    @patch(_PATCH_POST, return_value=_mock_success_response("urn:li:share:999"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_urn_extracted(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.platform_post_id == "urn:li:share:999"

    @patch(_PATCH_POST, return_value=_mock_success_response("urn:li:share:999"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_url_format(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.post_url == "https://www.linkedin.com/feed/update/urn:li:share:999"

    @patch(_PATCH_POST, return_value=_mock_success_response())
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_published_at_set(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.published_at is not None

    @patch(_PATCH_POST, return_value=_mock_success_response())
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_id_matches(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        post = _make_post()
        result = pub.publish(post)
        assert result.post_id == post.id

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_sends_bearer_header(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = LinkedInPublisher()
        pub.publish(_make_post())
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer li-token-abc"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_sends_restli_protocol_header(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = LinkedInPublisher()
        pub.publish(_make_post())
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["X-Restli-Protocol-Version"] == "2.0.0"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_ugc_payload_author(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = LinkedInPublisher()
        pub.publish(_make_post())
        payload = mock_post.call_args.kwargs["json"]
        assert payload["author"] == "urn:li:person:person-xyz"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_ugc_payload_content(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = LinkedInPublisher()
        pub.publish(_make_post(content="My LinkedIn post"))
        payload = mock_post.call_args.kwargs["json"]
        share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert share["shareCommentary"]["text"] == "My LinkedIn post"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_uses_edited_content_when_available(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = LinkedInPublisher()
        post = _make_post(content="original", edited_content="revised for LinkedIn")
        pub.publish(post)
        payload = mock_post.call_args.kwargs["json"]
        share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert share["shareCommentary"]["text"] == "revised for LinkedIn"


# ---------------------------------------------------------------------------
# publish — missing credentials
# ---------------------------------------------------------------------------


class TestLinkedInPublishMissingCreds:
    @patch(_PATCH_CREDS, return_value={})
    def test_returns_failure(self, _mock_creds):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.success is False

    @patch(_PATCH_CREDS, return_value={})
    def test_error_mentions_credentials(self, _mock_creds):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert "LINKEDIN" in result.error

    @patch(_PATCH_CREDS, return_value={"access_token": "tok"})
    def test_missing_person_id_returns_failure(self, _mock_creds):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.success is False

    @patch(_PATCH_CREDS, return_value={})
    def test_no_api_call_made(self, _mock_creds):
        with patch(_PATCH_POST) as mock_post:
            pub = LinkedInPublisher()
            pub.publish(_make_post())
            mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# publish — HTTP errors
# ---------------------------------------------------------------------------


class TestLinkedInPublishHTTPErrors:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_http_status_error_raises_publish_error(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 401
        resp.text = "Unauthorized"
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=resp
        )
        pub = LinkedInPublisher()
        with pytest.raises(PublishError, match="LinkedIn API error"):
            pub.publish(_make_post())

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_connection_error_raises_publish_error(self, _mock_creds, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        pub = LinkedInPublisher()
        with pytest.raises(PublishError, match="LinkedIn request failed"):
            pub.publish(_make_post())

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_timeout_error_raises_publish_error(self, _mock_creds, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Timed out")
        pub = LinkedInPublisher()
        with pytest.raises(PublishError, match="LinkedIn request failed"):
            pub.publish(_make_post())


# ---------------------------------------------------------------------------
# publish — edge cases
# ---------------------------------------------------------------------------


class TestLinkedInPublishEdgeCases:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_missing_restli_id_header(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.success is True
        assert result.platform_post_id == ""
        assert result.post_url is None

    @patch(_PATCH_POST, return_value=_mock_success_response())
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_platform_field_is_linkedin(self, _mock_creds, _mock_post):
        pub = LinkedInPublisher()
        result = pub.publish(_make_post())
        assert result.platform == Platform.linkedin
