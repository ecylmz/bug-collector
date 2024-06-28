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

    return bug_fix

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

def extract_file_metrics(file):
    return {
        "change_type": file.change_type,
        "added_lines": file.added_lines,
        "deleted_lines": file.deleted_lines,
        "changed_methods_count": len(file.changed_methods),
        "nloc": file.nloc,
        "complexity": file.complexity,
        "token_count": file.token_count
    }

# TODO
# aynı hash'e sahip varsa atla hesapla
# içerisinde go kodu olmayan komitleri de atla

def extract_commit_metrics(sha):
    commit = gr.get_commit(sha)
    modified_files = commit.modified_files
    mf_results = {"total_token_count": 0, "total_nloc": 0, "total_complexity": 0, "total_changed_method_count": 0}
    for mf in modified_files:
        if ".go" not in mf.filename:
            continue
        mf_result = extract_file_metrics(mf)
        mf_results["total_token_count"] += mf_result["token_count"] if mf_result["token_count"] is not None else 0
        mf_results["total_nloc"] += mf_result["nloc"] if mf_result["nloc"] is not None else 0
        mf_results["total_complexity"] += mf_result["complexity"] if mf_result["complexity"] is not None else 0
        mf_results["total_changed_method_count"] += mf_result["changed_methods_count"] if mf_result["changed_methods_count"] is not None else 0


    commit_result = {
        "sha": sha,
        "deletions": commit.deletions,
        "insertions": commit.insertions,
        "net_lines": commit.insertions - commit.deletions,
        "files": commit.files,
        "dmm_unit_size": commit.dmm_unit_size,
        "dmm_unit_complexity": commit.dmm_unit_complexity,
        "dmm_unit_interfacing": commit.dmm_unit_interfacing
    }

    if mf_results['total_complexity'] == 0 or commit_result["dmm_unit_complexity"] is None:
        return None
    return {**commit_result, **mf_results}


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

    # issue listesinde pr'ın sha bilgisine erişilemiyor. PR id'sinden tek tek pr detaylarını da çekmek gerekiyor.
    output = subprocess.run(command, capture_output=True, text=True)
    return json.loads(output.stdout)


if __name__ == '__main__':
    # GitHub'tan bug fix yapan pr'ları json olarak çek ve bir dosyaya kaydet
    prs = bug_fix_prs(projects[0]['repo'])
    write_json_to_file(prs, "prs/consul-bug-issues.json")

    # verisetinin içereceği alanlar
    headers = [
        "sha",
        "deletions",
        "insertions",
        "net_lines",
        "files",
        "dmm_unit_size",
        "dmm_unit_complexity",
        "dmm_unit_interfacing",
        "total_token_count",
        "total_nloc",
        "total_complexity",
        "total_changed_method_count"
    ]

    # Gelen verilerin bug fix yaptığını ve bug içermediğini varsayıyoruz.
    csvfile = open('consul-non-bugs.csv', 'w', newline='', encoding='utf-8')
    c = csv.DictWriter(csvfile, fieldnames=headers)
    c.writeheader()

    pr_fixes_commits = []
    all_pr_details = []
    for pr in prs:
        try:
            pr_details = get_pr_details(pr['number'])
            all_pr_details.append(pr_details)
            commit_sha = pr_details['merge_commit_sha']
            row = extract_commit_metrics(commit_sha)
            if row:
                c.writerow(row)
                pr_fixes_commits.append(commit_sha)
            # İşlem yapılacak kod buraya gelecek
        except Exception as e:
            print(e)
            # Hata oluştuğunda yapılacak işlemler buraya gelecek
            continue  # Hata olduğunda döngünün başına dön ve bir sonraki öğeye geç
    csvfile.close()
    write_json_to_file(all_pr_details, "prs/consul_bug_fix_pr_details.json")

    csvfile = open('consul-bugs.csv', 'w', newline='', encoding='utf-8')
    # headers = ['sha', 'dmm_unit_size', 'dmm_unit_complexity', 'dmm_unit_interfacing', 'deletions', 'insertions', 'lines']
    c = csv.DictWriter(csvfile, fieldnames=headers)
    c.writeheader()

    buggy_commits_list = []
    for commit_sha in pr_fixes_commits:
        try:
            commit = gr.get_commit(commit_sha)
            buggy_commits = gr.get_commits_last_modified_lines(commit)
            for bc in buggy_commits.values():
                for com in bc:
                    if com not in buggy_commits_list:
                        row = extract_commit_metrics(com)
                        if row:
                            c.writerow(row)
                            buggy_commits_list.append(com)
        except Exception as e:
            print(e)
            # Hata oluştuğunda yapılacak işlemler buraya gelecek
            continue  # Hata olduğunda döngünün başına dön ve bir sonraki öğeye geç
    csvfile.close()

