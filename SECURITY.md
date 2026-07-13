# Security Policy

## Supported versions

NV-SynthForge is currently an MVP. Security fixes are applied to the latest code on the `main` branch; there is no separately supported release line yet.

| Version | Supported |
| --- | --- |
| Latest `main` | Yes |
| Older snapshots or forks | No |

## Reporting a vulnerability

Please do **not** open a public issue, discussion, or pull request containing exploit details.

Use the repository's private **Security → Report a vulnerability** workflow if GitHub private vulnerability reporting is enabled. If it is not available, contact the repository owner privately and ask for a secure reporting channel without including sensitive details in a public forum.

Include, when safe to do so:

- affected commit or version;
- impacted component and configuration;
- reproduction steps or a minimal proof of concept;
- expected impact;
- suggested mitigation, if known;
- whether the report involves exposed credentials or generated artifacts.

Maintainers should acknowledge receipt as soon as practical, validate the report, coordinate a fix and disclosure timeline, and credit the reporter if requested. No fixed response-time SLA is promised for the MVP.

## Security assumptions and operator responsibilities

- Offline mode avoids the NVIDIA API but does not make generated artifacts safe for every use.
- `NVIDIA_API_KEY` is a server secret. Store it in a local ignored `.env` for development or a managed secret store in production.
- Never place secrets in `NEXT_PUBLIC_*` variables; those values are delivered to browsers.
- Local artifacts may contain realistic-looking synthetic records. Apply access controls, retention, and secure deletion appropriate to the environment.
- The local filesystem is not a shared or durable production artifact store.
- Native renderers and their OS packages expand the supply-chain and execution surface; pin and scan them.
- External provider requests should use only intended synthetic/schema inputs. Do not submit real personal, confidential, regulated, or proprietary data without an approved data-handling review.
- Public deployments require an explicit authentication/authorization design, restrictive CORS, rate limiting, request-size limits, and resource quotas. These controls are not claimed by the MVP.

## Secret exposure response

If a credential is committed or logged:

1. Revoke or rotate it immediately at the provider.
2. Remove it from active branches and deployment configuration.
3. Review provider and application logs for misuse.
4. Purge Git history only when necessary; history rewriting does not replace rotation.
5. Document the incident and add prevention (secret scanning, least privilege, shorter-lived credentials).
