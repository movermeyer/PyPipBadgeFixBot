import time

from github import Github, GithubException


GITHUB_TOKEN_FILE = ".github_token"

# Fiddler (https://www.telerik.com/fiddler) support
# import os
# os.environ['http_proxy'] = 'http://127.0.0.1:8888'
# os.environ['https_proxy'] = 'https://127.0.0.1:8888'


class RepoExistsException(Exception):
    pass


class ExtendedGitHub(object):
    def __init__(self, token):
        self.github = Github(token)

    def create_fork(self, original_repo):
        user = self.github.get_user()

        # Since forking `thieman/dagobah` and `Littlegump/dagobah` both result in `movemeyer/dagoba`, I'm going to explode in order to avoid problems.
        try:
            resulting_repo_name = f"{user.login}/{original_repo.name}"
            existing_repo = self.github.get_repo(resulting_repo_name)
            raise RepoExistsException(f"Repository '{existing_repo.full_name}' already exists.")
        except GithubException as exc:
            if exc.status == 404 and exc.data["message"] == "Not Found":
                pass
            else:
                raise

        forked_repo = user.create_fork(original_repo)
        return forked_repo

    def create_branch(self, original_repo, forked_repo, branch_name):
        current_sha = forked_repo.get_git_ref(f"heads/{original_repo.default_branch}").object.sha
        try:
            forked_repo.create_git_ref(f"refs/heads/{branch_name}", current_sha)
        except GithubException as exc:
            if exc.status == 422 and exc.data["message"] == "Reference already exists":
                # Fork already exists. Perhaps the program crashed and restarted.
                pass
            else:
                raise

    def make_commit(self, repository, branch, filepath, new_contents, commit_message):
        old_file_sha = repository.get_file_contents(filepath, ref=f"heads/{branch}").sha
        repository.update_file(filepath, commit_message, new_contents.encode(), old_file_sha, branch=branch)

    def make_pull_request(self, original_repo, branch, title, description):
        user = self.github.get_user().login
        result = original_repo.create_pull(title=title, body=description, head=f"{user}:{branch}", base=original_repo.default_branch)
        return result

    def update_file(self, target_project, branch_name, filepath, new_contents, commit_message, pull_request_title, pull_request_message):
        original_repo = self.github.get_repo(target_project)
        if original_repo.archived:
            # While some other operation will also raise this Exception, this allows us to catch it sooner.
            raise GithubException(status=403, data={"message": "Repository was archived so is read-only."})

        forked_repo = self.create_fork(original_repo)
        time.sleep(10)  # Hacky workaround to the fact that forks are done asyncronously. TODO: Figure out the proper way
        self.create_branch(original_repo, forked_repo, branch_name)
        self.make_commit(forked_repo, branch_name, filepath, new_contents, commit_message)
        pull_request = self.make_pull_request(original_repo, branch_name, pull_request_title, pull_request_message)
        return pull_request
