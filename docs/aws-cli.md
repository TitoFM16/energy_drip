# AWS CLI access

This project uses an explicit named AWS CLI profile. Do not configure or depend on the
`default` profile: this machine is used with multiple AWS accounts and projects.

AWS configuration and temporary login tokens belong in the macOS user's standard `~/.aws`
directory. Never copy `~/.aws`, access keys, login cache files, or credentials into this
repository or one of its Git worktrees.

## Prerequisites

AWS CLI v2.32 or later is required for browser login:

```bash
aws --version
```

On this Mac it is installed with Homebrew:

```bash
brew install awscli
```

## Configure and log in

Set only this project's named profile:

```bash
aws configure set region us-east-1 --profile energy-drip-dev
aws configure set output json --profile energy-drip-dev
```

Authenticate using the existing AWS Management Console identity:

```bash
aws login --profile energy-drip-dev
```

AWS CLI opens a browser. Sign in to the Energy Drip AWS account and approve local development
access. The CLI creates temporary credentials, refreshes them during the session, and caches
them under `~/.aws/login/cache`. No long-lived access key is required.

If the browser cannot open on the same machine, run:

```bash
aws login --profile energy-drip-dev --remote
```

Do not omit `--profile`: doing so can create or update the `default` profile. Do not create
long-lived IAM access keys for ordinary developer or agent access.

## Identity requirements

Do not use the AWS account root identity for ordinary CLI or agent operations. If identity
verification returns an ARN ending in `:root`, use that session only to establish a protected,
non-root administrative identity, then log out. Enable MFA on the root account and reserve it
for tasks that specifically require root.

The preferred routine identity is a least-privilege IAM role or IAM Identity Center permission
set. An IAM user used with `aws login` needs Console access, MFA, the permissions required for
the project, and AWS's `SignInLocalDevelopmentAccess` managed policy. Avoid broad administrator
permissions for Codex or Claude.

## Verify the selected account

Never begin work by assuming the profile points to the intended account. Verify it:

```bash
aws sts get-caller-identity --profile energy-drip-dev
aws configure get region --profile energy-drip-dev
```

Compare the returned `Account` ID and ARN with the expected project account before making
changes. Stop if the ARN ends in `:root`. Do not paste the account ID, ARN, or temporary
credentials into source files, issue trackers, or chat unless necessary.

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
2. Show the account and role being used and refuse to continue as root.
3. Confirm the intended region.
4. Use read-only discovery before mutations.
5. Request confirmation before destructive or production-impacting operations.

Agent sandboxes can still require approval for network access or for reading the user's AWS
configuration. An expired login session requires the human user to run `aws login` again.

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

End only this profile's temporary session:

```bash
aws logout --profile energy-drip-dev
```

## Troubleshooting

If the CLI reports an expired or invalid login token:

```bash
aws login --profile energy-drip-dev
```

If it cannot find the profile, configure its region again without changing the default
profile, then log in:

```bash
aws configure set region us-east-1 --profile energy-drip-dev
aws login --profile energy-drip-dev
```

If an agent cannot access AWS while the command works in your terminal, verify that the agent
runs as the same macOS user and grant the agent's requested filesystem/network approval. Do
not solve sandbox access by copying credentials into the repository.
