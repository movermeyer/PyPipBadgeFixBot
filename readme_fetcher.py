import requests

from bs4 import BeautifulSoup


class MissingReadmeException(Exception):
    pass


def fetch_readme(github_project):
    readme_url, readme_filepath = get_readme_url(github_project)
    if readme_url is None:
        raise MissingReadmeException(f"\tCouldn't determine readme URL for {github_project}")
    else:
        response = requests.get(readme_url)
        response.raise_for_status()
        return (response.text, readme_filepath)


def get_readme_url(project):
    response = requests.get(f"https://github.com/{project}")
    soup = BeautifulSoup(response.text, "html.parser")

    default_branch_button = next((button for button in soup.find_all('button') if button.attrs.get("aria-label") == "Switch branches or tags"), None)
    if default_branch_button is None:
        return (None, None)
    default_branch_span = next((span for span in default_branch_button.find_all('span') if span.attrs.get("class") == ["js-select-button", "css-truncate-target"]), None)
    if default_branch_span is None:
        return (None, None)
    default_branch = default_branch_span.get_text().strip()

    for h3 in soup.find_all('h3'):
        if len([x for x in h3.find_all('svg')]) > 0:
            # Sometimes the README is not in the root.
            # Get the navigation table and check if the readme is in the root.
            # Otherwise check "docs" directory.
            filepath = "".join([line.strip() for line in h3.get_text() if line.strip()])
            result = f"https://raw.githubusercontent.com/{project}/{default_branch}/{filepath}"
            break
    else:
        result = None
        filepath = None
    return (result, filepath)
