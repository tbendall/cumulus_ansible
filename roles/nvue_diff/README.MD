```md
# nvue_diff role

Runs `nv config diff` to compare NVUE configuration revisions and renders a Markdown report.

## Variables
- `nvue_revid` (required): target revision id to compare against base
- `nvue_diff_base` (default: applied)
- `nvue_diff_format` (default: commands) => uses `-o commands`
- `nvue_diff_write_report` (default: true)
- `nvue_diff_enforce` (default: false) => fail if fail-patterns match

## Example
```yaml
- name: Create revision
  nvidia.nvue.config:
    state: new
  register: revision

# ... build candidate ...

- name: Diff candidate vs applied and produce report
  include_role:
    name: nvue_diff
  vars:
    nvue_revid: "{{ revision.revid }}"
    nvue_diff_base: "applied"
    nvue_diff_enforce: true