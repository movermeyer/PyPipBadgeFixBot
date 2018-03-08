import csv
import sqlite3


from create_pull_request import ExtendedGitHub, RepoExistsException
from github import GithubException
from pypip_dot_in_helpers import replace_in_readme
from readme_fetcher import fetch_readme, MissingReadmeException
from urllib.parse import quote


DATABASE_FILE = "pypi_details.db"
BLACKLIST_FILE = "blacklist.csv"
GITHUB_TOKEN_FILE = ".github_token"


def main(max_pull_requests, min_download_count):
    black_list = set()
    with open(BLACKLIST_FILE, 'r') as fin:
        reader = csv.reader(fin, delimiter=',')
        black_list = set([row[0] for row in reader if len(row) > 0])

    with open(GITHUB_TOKEN_FILE, 'r') as fin:
        github_token = fin.read()

    github = ExtendedGitHub(github_token)

    conn = sqlite3.connect(DATABASE_FILE)

    conn.execute('''CREATE TABLE IF NOT EXISTS pull_requests (
        project text NOT NULL PRIMARY KEY,
        number integer,
        state text,
        reason text
    );''')

    results = conn.execute("""
        SELECT readme.package, project, readme
        FROM pypi LEFT JOIN readme ON pypi.package = readme.package
        WHERE readme is not NULL
        AND project is not NULL
        AND num_downloads >= ?
        ORDER BY num_downloads ASC;
    """, (min_download_count,))

    # Hack to deal with Bug #4
    already_processed_base_names = set([row[0].split('/')[1] for row in conn.execute("""
        SELECT project FROM pull_requests;
    """)])

    pull_requests_made = 0
    already_fixed = 0

    try:
        for package, project, readme in results:
            if package in black_list or any([project.startswith(banned_org) for banned_org in ["sprockets", "inveniosoftware"]]):
                print(f"Skipping {package} since it is the blacklist.")
                continue

            if "pypip.in" not in readme:
                continue

            # Resolve the real project location, in case it was renamed.
            resolved_project = github.github.get_repo(project).full_name.lower()
            if project.lower() != resolved_project:
                print(f"It appears that {project} was moved to {resolved_project}")
                conn.execute("UPDATE pypi SET project = ? WHERE package = ?", (resolved_project, package))
                project = resolved_project

            pull_request_already_exists = next(conn.execute("SELECT COUNT(*) FROM pull_requests WHERE project = ?", (project,)))[0] > 0

            if pull_request_already_exists:
                print(f"Skipping '{package}' since a pull request was already made to it.")
                continue

            # Go and get the current README, in case it has changed
            try:
                readme, readme_filepath = fetch_readme(project)
                conn.execute("UPDATE readme SET readme = ? WHERE package = ?;", (readme, package))
            except MissingReadmeException:
                print(f"Skipping '{package}' since we failed to fetch the readme.")
                continue

            if "pypip.in" not in readme:
                print(f"Skipping '{package}' since it no longer has pypip.in in it.")
                already_fixed += 1
                continue

            print(package, project)

            new_readme, n, found_download_endpoint, found_non_download_endpoint = replace_in_readme(readme)
            if n > 0 and readme != new_readme:

                # Create the pull request
                if found_non_download_endpoint:
                    explanation = f"""Hello, this is an auto-generated Pull Request. ([Feedback?](mailto:repobot@movermeyer.com?subject={quote(f"pypip.in Badge Bot Feedback: {package}")}))

Some time ago, [pypip.in](https://web.archive.org/web/20150318013508/https://pypip.in/) shut down. This broke the badges for a bunch of repositories, including `{package}`. Thankfully, an equivalent service is run by [shields.io](https://shields.io). This pull request changes the badge{'s' if n != 1 else ''} to use shields.io instead."""
                    if found_download_endpoint:
                        explanation += """

Unfortunately, [PyPI has removed download statistics from their API](https://mail.python.org/pipermail/distutils-sig/2013-May/020855.html), which means that even the shields.io "download count" badges are broken (they display "no longer available". See [this](https://github.com/badges/shields/issues/716)). So those badges should really be removed entirely. Since this is an automated process (and trying to automatically remove the badges from READMEs can be tricky), this pull request just replaces the URL with the shields.io syntax."""

                    try:
                        pull_request = github.update_file(project, "fix_badges", f"/{readme_filepath}", new_readme, "Switched broken pypip.in badges to shields.io", "Switched broken pypip.in badges to shields.io", explanation)
                        print(f'\t Created pull request')
                    except GithubException as exc:
                        if exc.status == 403 and exc.data["message"] == "Repository was archived so is read-only.":
                            print(f"\t Skipped: {exc.data['message']}")

                            # Update the blacklist
                            with open(BLACKLIST_FILE, 'a') as fout:
                                writer = csv.writer(fout, delimiter=',')
                                writer.writerow([package.strip(), exc.data['message']])
                            continue
                        else:
                            raise
                    except RepoExistsException as exc:
                        print(f"\t Skipped: {exc}")
                        continue

                    conn.execute("INSERT OR REPLACE INTO pull_requests (project, number, state, reason) VALUES (?, ?, ?, ?);", (project, pull_request.number, pull_request.state, "pypip.in"))

                    pull_requests_made += 1

                    if pull_requests_made == max_pull_requests:
                        break
                else:
                    print(f"\tSkipping '{package}' since all pypip badges are download counts badges.")
            else:
                print(f"\tSkipping '{package}' since `replace_in_readme` didn't cause any changes.")
    finally:
        print(f"Created {pull_requests_made} pull requests. {already_fixed} were already fixed.")
        conn.commit()
        conn.close()


if __name__ == '__main__':
    main(100, 129678)
