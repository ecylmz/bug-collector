import subprocess

# https://accessibleai.dev/post/extracting-git-data-pydriller/

projects = [
    {'owner': 'hashicorp', 'repo': 'consul'},
]

def git_clone(repo_url, destination):
    """
    Clones a git repository from `repo_url` into `destination`.

    Parameters:
        repo_url (str): The URL of the git repository to clone.
        destination (str): The path where the repository will be cloned.

    Returns:
        bool: True if cloning was successful, False otherwise.
    """
    try:
        subprocess.run(["git", "clone", "git@github.com:hashicorp/consul"], check=True)
        return True
    except subprocess.CalledProcessError:
        print("Error: Cloning failed.")
        return False

if __name__ == '__main__':
    git_clone(projects[0], "/tmp")
