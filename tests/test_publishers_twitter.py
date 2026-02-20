"""Tests for marketing_engine.publishers.twitter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from marketing_engine.enums import ContentStream, Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.result import PublishResult
from marketing_engine.publishers.twitter import TwitterPublisher

_PATCH_CREDS = "marketing_engine.publishers.twitter.get_platform_credentials"
_PATCH_POST = "marketing_engine.publishers.twitter.httpx.post"

_VALID_CREDS = {"bearer_token": "test-bearer-token-123"}


def _make_post(
    content: str = "Build beautiful CLIs with Typer + Rich in Python.",
    edited_content: str | None = None,
    **kwargs,
) -> PostDraft:
    return PostDraft(
        brief_id="brief-1",
        stream=ContentStream.project_marketing,
        platform=Platform.twitter,
        content=content,
        hashtags=["python", "cli"],
        cta_url="https://typer.tiangolo.com",
        scheduled_time=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        edited_content=edited_content,
        **kwargs,
    )


def _mock_success_response(tweet_id: str = "1234567890") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 201
    resp.json.return_value = {"data": {"id": tweet_id}}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# TwitterPublisher.__init__ / platform
# ---------------------------------------------------------------------------


class TestTwitterPublisherInit:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_platform_is_twitter(self, _mock_creds):
        pub = TwitterPublisher()
        assert pub.platform == Platform.twitter

    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_calls_get_platform_credentials(self, mock_creds):
        TwitterPublisher()
        mock_creds.assert_called_once_with("twitter")

    @patch(_PATCH_CREDS, return_value={})
    def test_init_with_empty_creds(self, _mock_creds):
        pub = TwitterPublisher()
        assert pub._creds == {}


# ---------------------------------------------------------------------------
# validate_credentials
# ---------------------------------------------------------------------------


class TestTwitterValidateCredentials:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_valid_bearer_token(self, _mock_creds):
        pub = TwitterPublisher()
        assert pub.validate_credentials() is True

    @patch(_PATCH_CREDS, return_value={})
    def test_missing_bearer_token(self, _mock_creds):
        pub = TwitterPublisher()
        assert pub.validate_credentials() is False

    @patch(_PATCH_CREDS, return_value={"bearer_token": ""})
    def test_empty_bearer_token(self, _mock_creds):
        pub = TwitterPublisher()
        assert pub.validate_credentials() is False

    @patch(_PATCH_CREDS, return_value={"bearer_token": None})
    def test_none_bearer_token(self, _mock_creds):
        pub = TwitterPublisher()
        assert pub.validate_credentials() is False


# ---------------------------------------------------------------------------
# publish — success cases
# ---------------------------------------------------------------------------


class TestTwitterPublishSuccess:
    @patch(_PATCH_POST, return_value=_mock_success_response())
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_returns_publish_result(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert isinstance(result, PublishResult)

    @patch(_PATCH_POST, return_value=_mock_success_response("9876543210"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_success_flag(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.success is True

    @patch(_PATCH_POST, return_value=_mock_success_response("9876543210"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_tweet_id_extracted(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.platform_post_id == "9876543210"

    @patch(_PATCH_POST, return_value=_mock_success_response("9876543210"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_url_format(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.post_url == "https://twitter.com/i/status/9876543210"

    @patch(_PATCH_POST, return_value=_mock_success_response("111"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_published_at_set(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.published_at is not None

    @patch(_PATCH_POST, return_value=_mock_success_response("111"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_id_matches(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        post = _make_post()
        result = pub.publish(post)
        assert result.post_id == post.id

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_sends_correct_payload(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = TwitterPublisher()
        pub.publish(_make_post(content="Hello world"))
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"] == {"text": "Hello world"}

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_sends_bearer_header(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = TwitterPublisher()
        pub.publish(_make_post())
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-bearer-token-123"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_uses_edited_content_when_available(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_success_response()
        pub = TwitterPublisher()
        post = _make_post(content="original", edited_content="revised tweet")
        pub.publish(post)
        assert mock_post.call_args.kwargs["json"]["text"] == "revised tweet"


# ---------------------------------------------------------------------------
# publish — missing credentials
# ---------------------------------------------------------------------------


class TestTwitterPublishMissingCreds:
    @patch(_PATCH_CREDS, return_value={})
    def test_returns_failure(self, _mock_creds):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.success is False

    @patch(_PATCH_CREDS, return_value={})
    def test_error_mentions_bearer_token(self, _mock_creds):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert "BEARER_TOKEN" in result.error

    @patch(_PATCH_CREDS, return_value={})
    def test_no_api_call_made(self, _mock_creds):
        with patch(_PATCH_POST) as mock_post:
            pub = TwitterPublisher()
            pub.publish(_make_post())
            mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# publish — HTTP errors
# ---------------------------------------------------------------------------


class TestTwitterPublishHTTPErrors:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_http_status_error_raises_publish_error(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 403
        resp.text = "Forbidden"
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=resp
        )
        pub = TwitterPublisher()
        with pytest.raises(PublishError, match="Twitter API error"):
            pub.publish(_make_post())

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_connection_error_raises_publish_error(self, _mock_creds, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        pub = TwitterPublisher()
        with pytest.raises(PublishError, match="Twitter request failed"):
            pub.publish(_make_post())

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_timeout_error_raises_publish_error(self, _mock_creds, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Timed out")
        pub = TwitterPublisher()
        with pytest.raises(PublishError, match="Twitter request failed"):
            pub.publish(_make_post())


# ---------------------------------------------------------------------------
# publish — edge cases
# ---------------------------------------------------------------------------


class TestTwitterPublishEdgeCases:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_empty_data_in_response(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.json.return_value = {"data": {}}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.success is True
        assert result.platform_post_id == ""
        assert result.post_url is None

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_missing_data_key_in_response(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.json.return_value = {}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.success is True
        assert result.platform_post_id == ""

    @patch(_PATCH_POST, return_value=_mock_success_response("42"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_platform_field_is_twitter(self, _mock_creds, _mock_post):
        pub = TwitterPublisher()
        result = pub.publish(_make_post())
        assert result.platform == Platform.twitter
