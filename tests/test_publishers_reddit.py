"""Tests for marketing_engine.publishers.reddit."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from marketing_engine.enums import ContentStream, Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.reddit import RedditPublisher
from marketing_engine.publishers.result import PublishResult

_PATCH_CREDS = "marketing_engine.publishers.reddit.get_platform_credentials"
_PATCH_POST = "marketing_engine.publishers.reddit.httpx.post"

_VALID_CREDS = {
    "client_id": "reddit-client-id",
    "client_secret": "reddit-client-secret",
    "username": "testuser",
    "password": "testpass",
}


def _make_post(
    content: str = "My Reddit Title\nBody of the post with details.",
    subreddit: str | None = "Python",
    edited_content: str | None = None,
    **kwargs,
) -> PostDraft:
    return PostDraft(
        brief_id="brief-1",
        stream=ContentStream.project_marketing,
        platform=Platform.reddit,
        content=content,
        hashtags=["python", "cli"],
        cta_url="https://typer.tiangolo.com",
        scheduled_time=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        subreddit=subreddit,
        edited_content=edited_content,
        **kwargs,
    )


def _mock_token_response(token: str = "reddit-access-token") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"access_token": token}
    resp.raise_for_status.return_value = None
    return resp


def _mock_submit_response(
    url: str = "https://www.reddit.com/r/Python/comments/abc123/my_post/",
    post_id: str = "abc123",
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"json": {"data": {"url": url, "id": post_id}}}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# RedditPublisher.__init__ / platform
# ---------------------------------------------------------------------------


class TestRedditPublisherInit:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_platform_is_reddit(self, _mock_creds):
        pub = RedditPublisher()
        assert pub.platform == Platform.reddit

    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_calls_get_platform_credentials(self, mock_creds):
        RedditPublisher()
        mock_creds.assert_called_once_with("reddit")

    @patch(_PATCH_CREDS, return_value={})
    def test_init_with_empty_creds(self, _mock_creds):
        pub = RedditPublisher()
        assert pub._creds == {}


# ---------------------------------------------------------------------------
# validate_credentials
# ---------------------------------------------------------------------------


class TestRedditValidateCredentials:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_valid_credentials(self, _mock_creds):
        pub = RedditPublisher()
        assert pub.validate_credentials() is True

    @patch(_PATCH_CREDS, return_value={})
    def test_missing_all_credentials(self, _mock_creds):
        pub = RedditPublisher()
        assert pub.validate_credentials() is False

    @patch(
        _PATCH_CREDS,
        return_value={"client_id": "cid", "client_secret": "cs", "username": "u"},
    )
    def test_missing_password(self, _mock_creds):
        pub = RedditPublisher()
        assert pub.validate_credentials() is False

    @patch(
        _PATCH_CREDS,
        return_value={"client_secret": "cs", "username": "u", "password": "p"},
    )
    def test_missing_client_id(self, _mock_creds):
        pub = RedditPublisher()
        assert pub.validate_credentials() is False

    @patch(
        _PATCH_CREDS,
        return_value={
            "client_id": "",
            "client_secret": "cs",
            "username": "u",
            "password": "p",
        },
    )
    def test_empty_client_id(self, _mock_creds):
        pub = RedditPublisher()
        assert pub.validate_credentials() is False


# ---------------------------------------------------------------------------
# _get_access_token
# ---------------------------------------------------------------------------


class TestRedditGetAccessToken:
    @patch(_PATCH_POST, return_value=_mock_token_response("my-token"))
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_returns_token(self, _mock_creds, _mock_post):
        pub = RedditPublisher()
        token = pub._get_access_token()
        assert token == "my-token"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_sends_auth_tuple(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_token_response()
        pub = RedditPublisher()
        pub._get_access_token()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["auth"] == ("reddit-client-id", "reddit-client-secret")

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_sends_password_grant_data(self, _mock_creds, mock_post):
        mock_post.return_value = _mock_token_response()
        pub = RedditPublisher()
        pub._get_access_token()
        data = mock_post.call_args.kwargs["data"]
        assert data["grant_type"] == "password"
        assert data["username"] == "testuser"
        assert data["password"] == "testpass"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_empty_token_raises_publish_error(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.json.return_value = {"access_token": ""}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp
        pub = RedditPublisher()
        with pytest.raises(PublishError, match="empty access token"):
            pub._get_access_token()

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_missing_token_key_raises_publish_error(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.json.return_value = {}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp
        pub = RedditPublisher()
        with pytest.raises(PublishError, match="empty access token"):
            pub._get_access_token()

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_http_error_raises_publish_error(self, _mock_creds, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        pub = RedditPublisher()
        with pytest.raises(PublishError, match="Reddit OAuth failed"):
            pub._get_access_token()


# ---------------------------------------------------------------------------
# publish — success cases
# ---------------------------------------------------------------------------


class TestRedditPublishSuccess:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_returns_publish_result(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert isinstance(result, PublishResult)

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_success_flag(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.success is True

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_url_extracted(self, _mock_creds, mock_post):
        mock_post.side_effect = [
            _mock_token_response(),
            _mock_submit_response(url="https://reddit.com/r/Python/comments/xyz/"),
        ]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.post_url == "https://reddit.com/r/Python/comments/xyz/"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_id_extracted(self, _mock_creds, mock_post):
        mock_post.side_effect = [
            _mock_token_response(),
            _mock_submit_response(post_id="xyz789"),
        ]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.platform_post_id == "xyz789"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_published_at_set(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.published_at is not None

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_post_id_matches(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        post = _make_post()
        result = pub.publish(post)
        assert result.post_id == post.id

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_title_from_first_line(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        pub.publish(_make_post(content="My Title\nBody text here"))
        submit_call = mock_post.call_args_list[1]
        assert submit_call.kwargs["data"]["title"] == "My Title"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_body_from_remaining_lines(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        pub.publish(_make_post(content="My Title\nBody text here"))
        submit_call = mock_post.call_args_list[1]
        assert submit_call.kwargs["data"]["text"] == "Body text here"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_subreddit_in_submit_data(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        pub.publish(_make_post(subreddit="learnpython"))
        submit_call = mock_post.call_args_list[1]
        assert submit_call.kwargs["data"]["sr"] == "learnpython"

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_uses_edited_content_when_available(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        post = _make_post(content="Original\nOld body", edited_content="Revised\nNew body")
        pub.publish(post)
        submit_call = mock_post.call_args_list[1]
        assert submit_call.kwargs["data"]["title"] == "Revised"
        assert submit_call.kwargs["data"]["text"] == "New body"


# ---------------------------------------------------------------------------
# publish — missing credentials
# ---------------------------------------------------------------------------


class TestRedditPublishMissingCreds:
    @patch(_PATCH_CREDS, return_value={})
    def test_returns_failure(self, _mock_creds):
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.success is False

    @patch(_PATCH_CREDS, return_value={})
    def test_error_mentions_reddit(self, _mock_creds):
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert "Reddit" in result.error

    @patch(_PATCH_CREDS, return_value={})
    def test_no_api_call_made(self, _mock_creds):
        with patch(_PATCH_POST) as mock_post:
            pub = RedditPublisher()
            pub.publish(_make_post())
            mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# publish — missing subreddit
# ---------------------------------------------------------------------------


class TestRedditPublishMissingSubreddit:
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_none_subreddit_returns_failure(self, _mock_creds):
        pub = RedditPublisher()
        result = pub.publish(_make_post(subreddit=None))
        assert result.success is False

    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_error_mentions_subreddit(self, _mock_creds):
        pub = RedditPublisher()
        result = pub.publish(_make_post(subreddit=None))
        assert "subreddit" in result.error.lower()

    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_no_api_call_for_missing_subreddit(self, _mock_creds):
        with patch(_PATCH_POST) as mock_post:
            pub = RedditPublisher()
            pub.publish(_make_post(subreddit=None))
            mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# publish — HTTP errors
# ---------------------------------------------------------------------------


class TestRedditPublishHTTPErrors:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_submit_status_error_raises_publish_error(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 403
        resp.text = "Forbidden"
        submit_resp = MagicMock(spec=httpx.Response)
        submit_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=resp
        )
        mock_post.side_effect = [_mock_token_response(), submit_resp]
        pub = RedditPublisher()
        with pytest.raises(PublishError, match="Reddit API error"):
            pub.publish(_make_post())

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_submit_connection_error_raises_publish_error(self, _mock_creds, mock_post):
        mock_post.side_effect = [
            _mock_token_response(),
            httpx.ConnectError("Connection refused"),
        ]
        pub = RedditPublisher()
        with pytest.raises(PublishError, match="Reddit request failed"):
            pub.publish(_make_post())

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_token_failure_propagates(self, _mock_creds, mock_post):
        mock_post.side_effect = httpx.ConnectError("No internet")
        pub = RedditPublisher()
        with pytest.raises(PublishError, match="Reddit OAuth failed"):
            pub.publish(_make_post())


# ---------------------------------------------------------------------------
# publish — edge cases
# ---------------------------------------------------------------------------


class TestRedditPublishEdgeCases:
    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_single_line_content_empty_body(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        pub.publish(_make_post(content="Title only no newline"))
        submit_call = mock_post.call_args_list[1]
        assert submit_call.kwargs["data"]["title"] == "Title only no newline"
        assert submit_call.kwargs["data"]["text"] == ""

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_title_truncated_at_300_chars(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        long_title = "A" * 400
        pub.publish(_make_post(content=f"{long_title}\nBody"))
        submit_call = mock_post.call_args_list[1]
        assert len(submit_call.kwargs["data"]["title"]) == 300

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_response_missing_json_key(self, _mock_creds, mock_post):
        resp = MagicMock(spec=httpx.Response)
        resp.json.return_value = {"status": "ok"}
        resp.raise_for_status.return_value = None
        mock_post.side_effect = [_mock_token_response(), resp]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.success is True
        assert result.platform_post_id is None
        assert result.post_url is None

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_platform_field_is_reddit(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        result = pub.publish(_make_post())
        assert result.platform == Platform.reddit

    @patch(_PATCH_POST)
    @patch(_PATCH_CREDS, return_value=_VALID_CREDS)
    def test_submit_kind_is_self(self, _mock_creds, mock_post):
        mock_post.side_effect = [_mock_token_response(), _mock_submit_response()]
        pub = RedditPublisher()
        pub.publish(_make_post())
        submit_call = mock_post.call_args_list[1]
        assert submit_call.kwargs["data"]["kind"] == "self"
