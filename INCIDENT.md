# 事故対応 Incident Response

When something breaks. No theory — just do the steps.

---

## 1. Dependency has a CVE

**First:** Check if you're actually affected.
```bash
pip-audit                              # scan for known CVEs
pip show <package>                     # check your installed version
```

**Then:**
- Read the CVE — does it affect how you use the package, or an unrelated feature?
- `pip install <package> --upgrade` to get the patched version
- Run tests: `pytest` — make sure the update didn't break anything
- `pip freeze > requirements.txt` to lock the new version
- Commit: `git add requirements.txt && git commit -m "fix: upgrade <package> (CVE-XXXX-XXXXX)"`

---

## 2. Secrets committed to git

**First:** Rotate the secret NOW. Don't clean history first — assume it's already stolen.

**Then:**
- Revoke the old key/token in whatever service issued it
- Generate a new one, store it in an env var or `.env` (never in code)
- Scrub git history:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch <file>" \
  --prune-empty -- --all
git push --force
```
- Add the file to `.gitignore`
- Check: `trufflehog3 .` to confirm it's gone
- If the repo was ever public, even briefly — treat every secret in it as compromised

---

## 3. Tests failing after a change

**First:** Read the error message. Seriously — the answer is usually right there.

**Then:**
- Run just the failing test to get full output:
```bash
pytest tests/test_file.py::test_name -v
```
- If unclear which change broke it, use git bisect:
```bash
git bisect start
git bisect bad                         # current commit is broken
git bisect good <last-known-good-hash> # this one worked
# git checks out a middle commit — run tests, then:
git bisect good                        # or git bisect bad
# repeat until it finds the breaking commit
git bisect reset                       # done, back to normal
```
- Check `git diff <good-hash>` to see exactly what changed

---

## 4. Doji scan found a critical finding

**First:** Read the finding. Doji explains what it found and why it matters.

**Then:**
- Check if it's a real issue or a false positive:
  - Does user input actually reach that code path?
  - Is there validation/sanitization you wrote that Doji missed?
- If real — fix it, rescan, confirm it's gone:
```bash
doji scan . --diff                     # only scan changed lines
```
- If false positive — suppress it so it doesn't keep firing:
  - Add a `# doji:ignore` comment on that line, or
  - Add the rule to `.doji.toml` under `[ignore]`
- Critical findings in security rules (secrets, injection, traversal) are real until proven otherwise

---

## 5. Something broke after deployment

**First:** Revert to the last working state.
```bash
git log --oneline -10                  # find the last good commit
git revert <bad-commit-hash>           # creates a new commit undoing it
git push
```

**Then:**
- Figure out what changed: `git diff <good>..<bad>`
- Check recent commits: `git log --oneline --since="2 hours ago"`
- If multiple commits caused it, revert a range:
```bash
git revert --no-commit <oldest-bad>..<newest-bad>
git commit -m "revert: roll back broken changes"
```
- Fix the actual bug on a branch, test it, then merge back

---

## General rules

- **Don't panic.** Revert first, investigate second.
- **Don't push fixes without testing.** You'll create a second incident.
- **Write down what happened.** Future you will forget. One line in the commit message is enough.
