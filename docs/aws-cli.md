# AWS CLI access

This project uses an explicit named AWS CLI profile. Do not configure or depend on the
`default` profile: this machine is used with multiple AWS accounts and projects.

AWS configuration and temporary login tokens belong in the macOS user's standard
`~/.aws` directory. Never copy `~/.aws`, access keys, SSO cache files, or credentials into
this repository or one of its Git worktrees.

## Prerequisites

AWS CLI v2 is required:

```bash
aws --version
```

On this Mac it is installed with Homebrew:

```bash
brew install awscli
```

## Configure this project's profile once

Ask the AWS administrator for the IAM Identity Center start URL, SSO region, AWS account,
and least-privilege permission set assigned to this project. Then run:

```bash
aws configure sso --profile energy-drip-dev
```

Suggested values where the wizard asks for names:

- SSO session name: `energy-drip`
- CLI profile name: `energy-drip-dev`
- Output format: `json`

Choose the account, role, and region provided by the administrator. Do not configure access
under the `default` profile and do not create long-lived IAM access keys for normal developer
or agent access.

The profile configuration is stored in `~/.aws/config`. SSO issues temporary tokens under
`~/.aws/sso/cache`; it does not require secrets in the repository.

## Log in

Start or refresh the project's SSO session explicitly:

```bash
aws sso login --profile energy-drip-dev
```

The command opens AWS authentication in a browser. A human must complete authentication and
MFA when requested. Codex or Claude can use the resulting temporary session afterward.

If browser launch is unavailable, use device authorization:

```bash
aws sso login --profile energy-drip-dev --use-device-code
```

## Verify the selected account

Never begin work by assuming the profile points to the intended account. Verify it:

```bash
aws sts get-caller-identity --profile energy-drip-dev
aws configure get region --profile energy-drip-dev
```

Compare the returned `Account` ID and ARN with the expected project account before making
changes. Do not paste the account ID, ARN, or temporary credentials into source files, issue
trackers, or chat unless necessary.

Run every command with the explicit profile:

```bash
aws s3api list-buckets --profile energy-drip-dev
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --profile energy-drip-dev
```

For a sequence of commands in one terminal, a shell-scoped environment variable is acceptable:

```bash
export AWS_PROFILE=energy-drip-dev
aws sts get-caller-identity
```

Unset it before switching projects:

```bash
unset AWS_PROFILE
```

Do not add `AWS_PROFILE` globally to `.zshrc`; doing so can accidentally direct another
project to this account. Prefer `--profile energy-drip-dev`, or use a directory-scoped tool
such as `direnv` with a local, ignored `.envrc` after reviewing its contents.

## Codex and Claude usage

Both agents should run under the same macOS user and use the explicit profile:

```bash
aws <service> <operation> --profile energy-drip-dev
```

Before an agent performs AWS work, ask it to:

1. Run `aws sts get-caller-identity --profile energy-drip-dev`.
2. Show the account and role being used.
3. Confirm the intended region.
4. Use read-only discovery before mutations.
5. Request confirmation before destructive or production-impacting operations.

Agent sandboxes can still require approval for network access or for reading the user's AWS
configuration. An expired SSO session requires the human user to run `aws sso login` again.

## Multiple environments

Use separate named profiles and permission sets instead of sharing one powerful role:

```text
energy-drip-dev
energy-drip-staging
energy-drip-prod-readonly
energy-drip-prod-deploy
```

Always include the selected profile in commands. Production deployment access should be
short-lived, least-privilege, MFA-protected, and separate from ordinary development access.

List configured profile names without displaying credentials:

```bash
aws configure list-profiles
```

Log out of the project's SSO session when needed:

```bash
aws sso logout
```

Note that `aws sso logout` removes all cached AWS SSO sessions on the machine, not only this
profile. Normally it is sufficient to let temporary sessions expire.

## Troubleshooting

If the CLI reports an expired or invalid SSO token:

```bash
aws sso login --profile energy-drip-dev
```

If it cannot find the profile, configure it again without changing the default profile:

```bash
aws configure sso --profile energy-drip-dev
```

If an agent cannot access AWS while the command works in your terminal, verify that the agent
runs as the same macOS user and grant the agent's requested filesystem/network approval. Do
not solve sandbox access by copying credentials into the repository.
