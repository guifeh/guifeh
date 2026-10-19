"""Regression tests for profile statistics."""

from unittest.mock import Mock

import pytest

from generator.github_api import GitHubAPI


def response(data):
    return Mock(json=Mock(return_value=data))


def test_stats_count_last_year_commits_without_counting_other_activity(monkeypatch):
    api = GitHubAPI("guifeh", token="test-token")
    request = Mock(side_effect=[
        response({"data": {"user": {
            "contributionsCollection": {"totalCommitContributions": 105, "restrictedContributionsCount": 12},
            "repositories": {"totalCount": 60, "nodes": [{"stargazerCount": 1}]},
            "pullRequests": {"totalCount": 17}, "issues": {"totalCount": 1},
        }}}),
    ])
    monkeypatch.setattr(api, "_request", request)
    monkeypatch.setattr(api, "_paginate_repos", lambda: iter([[{"stargazers_count": 1}]]))

    assert api.fetch_stats() == {"commits": 105, "stars": 1, "prs": 17, "issues": 1, "repos": 60}
    first_query = request.call_args_list[0].kwargs["json"]["query"]
    assert "privacy: PUBLIC" in first_query
    assert "restrictedContributionsCount" not in first_query
    assert "totalCommitContributions" in first_query
    assert request.call_count == 1


def test_stats_do_not_publish_estimates_when_graphql_fails(monkeypatch):
    api = GitHubAPI("guifeh", token="test-token")
    monkeypatch.setattr(api, "_request", Mock(return_value=response({"errors": [{"message": "unavailable"}]})))
    with pytest.raises(ValueError, match="GraphQL"):
        api.fetch_stats()


def test_generation_preserves_assets_when_stats_fail(monkeypatch):
    from argparse import Namespace
    from generator import main

    api = Mock()
    api.fetch_stats.side_effect = ValueError("API unavailable")
    monkeypatch.setattr(main, "GitHubAPI", Mock(return_value=api))
    builder = Mock()
    monkeypatch.setattr(main, "SVGBuilder", builder)

    with pytest.raises(SystemExit) as failure:
        main.generate(Namespace(demo=False))
    assert failure.value.code == 1
    builder.assert_not_called()
