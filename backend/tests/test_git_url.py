"""Unit tests for GitHub URL validation/normalization."""

import pytest

from app.utils.git import InvalidRepoUrlError, normalize_github_url

HOSTS = ["github.com"]


def test_normalizes_valid_url() -> None:
    assert (
        normalize_github_url("https://github.com/psf/requests", HOSTS)
        == "https://github.com/psf/requests.git"
    )


def test_strips_dot_git_and_trailing_path() -> None:
    assert (
        normalize_github_url("https://github.com/psf/requests.git/tree/main", HOSTS)
        == "https://github.com/psf/requests.git"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/psf/requests",          # non-https
        "https://gitlab.com/psf/requests",         # host not allow-listed
        "https://user:pass@github.com/psf/req",    # embedded credentials
        "https://github.com/onlyowner",            # missing repo
        "https://github.com/psf/re;po",            # illegal characters
        "not-a-url",                               # garbage
        "",                                        # empty
    ],
)
def test_rejects_bad_urls(url: str) -> None:
    with pytest.raises(InvalidRepoUrlError):
        normalize_github_url(url, HOSTS)
