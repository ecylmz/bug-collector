from pydriller import Git
import subprocess
import json
import csv

# https://accessibleai.dev/post/extracting-git-data-pydriller/

projects = [
    {'owner': 'hashicorp', 'repo': 'consul', 'label': 'type/bug'},
]

gr = Git('projects/consul')

def bug_fix_prs(repository):
    command = [
        "gh",
        "api",
        "--header",
        "Accept: application/vnd.github+json",
        "--method",
        "GET",
        "/repos/hashicorp/consul/issues",
        "-f",
        "state=closed",
        "-f",
        "labels=type/bug",
        "--paginate"
    ]

    # aşağıdaki komutta sha bilgisine erişilemiyor. PR id'sinden tek tek pr detaylarını da çekmek gerekiyor.
    output = subprocess.run(command, capture_output=True, text=True)
    prs = json.loads(output.stdout)
    bug_fix = []
    for pr in prs:
        if 'pull_request' in pr:
            bug_fix.append(pr)

    # print(bug_fix)
    # return json.loads(output.stdout)
    return bug_fix

def pr_details(pr_id):
    pass

def get_buggy_commits(fix_commit_sha):
    commit = gr.get_commit(fix_commit_sha)
    buggy_commits = gr.get_commits_last_modified_lines(commit)

    commits = []
    for commit in buggy_commits.values():
        record = {
            'hash': hash,
            'message': commit.msg,
            'author_name': commit.author.name,
            'author_email': commit.author.email,
            'author_date': commit.author_date,
            'author_tz': commit.author_timezone,
            'committer_name': commit.committer.name,
            'committer_email': commit.committer.email,
            'committer_date': commit.committer_date,
            'committer_tz': commit.committer_timezone,
            'in_main': commit.in_main_branch,
            'is_merge': commit.merge,
            'num_deletes': commit.deletions,
            'num_inserts': commit.insertions,
            'net_lines': commit.insertions - commit.deletions,
            'num_files': commit.files,
            'branches': ', '.join(commit.branches), # Comma separated list of branches the commit is found in
            # 'files': ', '.join(files), # Comma separated list of files the commit modifies
            'parents': ', '.join(commit.parents), # Comma separated list of parents
            # PyDriller Open Source Delta Maintainability Model (OS-DMM) stat. See https://pydriller.readthedocs.io/en/latest/deltamaintainability.html for metric definitions
            'dmm_unit_size': commit.dmm_unit_size,
            'dmm_unit_complexity': commit.dmm_unit_complexity,
            'dmm_unit_interfacing': commit.dmm_unit_interfacing,
        }
        # Omitted: modified_files (list), project_path, project_name
        commits.append(record)
    return buggy_commits


def write_json_to_file(data, filename):
    """
    Writes JSON data to a file.

    Parameters:
        data (dict): JSON data to write to the file.
        filename (str): Name of the file to write the JSON data to.
    """
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


def collect(project):
    pass

def extract_commit_metrics(sha):
    commit = gr.get_commit(sha)
    result = {
        "sha": sha,
        "dmm_unit_size": commit.dmm_unit_size,
        "dmm_unit_complexity": commit.dmm_unit_complexity,
        "dmm_unit_interfacing": commit.dmm_unit_interfacing,
        "deletions": commit.deletions,
        "insertions": commit.insertions,
        "lines": commit.lines
    }
    return result


def get_pr_details(pr_id):
    pr_path = f"/repos/hashicorp/consul/pulls/{pr_id}"
    command = [
        "gh",
        "api",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        pr_path
    ]

    # print(command)
    # aşağıdaki komutta sha bilgisine erişilemiyor. PR id'sinden tek tek pr detaylarını da çekmek gerekiyor.
    output = subprocess.run(command, capture_output=True, text=True)
    return json.loads(output.stdout)


if __name__ == '__main__':
    prs = bug_fix_prs(projects[0]['repo'])
    write_json_to_file(prs, "prs/consul-bug-issues.json")
    data = []
    csvfile = open('consul-non-bugs.csv', 'w', newline='', encoding='utf-8')
    headers = ['sha', 'dmm_unit_size', 'dmm_unit_complexity', 'dmm_unit_interfacing', 'deletions', 'insertions', 'lines']
    c = csv.DictWriter(csvfile, fieldnames=headers)
    c.writeheader()

    pr_fixes_commits = []
    for pr in prs:
        try:
            pr_details = get_pr_details(pr['number'])
            commit_sha = pr_details['merge_commit_sha']
            # data.append(extract_commit_metrics(commit_sha))
            row = extract_commit_metrics(commit_sha)
            c.writerow(row)
            pr_fixes_commits.append(commit_sha)
            # İşlem yapılacak kod buraya gelecek
        except Exception as e:
            print(e)
            # Hata oluştuğunda yapılacak işlemler buraya gelecek
            continue  # Hata olduğunda döngünün başına dön ve bir sonraki öğeye geç
    csvfile.close()

    csvfile = open('consul-bugs.csv', 'w', newline='', encoding='utf-8')
    headers = ['sha', 'dmm_unit_size', 'dmm_unit_complexity', 'dmm_unit_interfacing', 'deletions', 'insertions', 'lines']
    c = csv.DictWriter(csvfile, fieldnames=headers)
    c.writeheader()

    for commit_sha in pr_fixes_commits:
        try:
            commit = gr.get_commit(commit_sha)
            buggy_commits = gr.get_commits_last_modified_lines(commit)
            for bc in buggy_commits.values():
                for com in bc:
                    row = extract_commit_metrics(com)
                    c.writerow(row)
        except Exception as e:
            print(e)
            # Hata oluştuğunda yapılacak işlemler buraya gelecek
            continue  # Hata olduğunda döngünün başına dön ve bir sonraki öğeye geç
    csvfile.close()

