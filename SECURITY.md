# Security policy

## Reporting a vulnerability

Report privately through
[GitHub's private vulnerability reporting](https://github.com/aSel1x/Backend_Template/security/advisories/new).
Please do not open a public issue for anything exploitable.

Include what you did, what happened, and what you expected. A proof of concept helps but is not
required. Expect an acknowledgement within a few days.

## Supported versions

| Version | Supported |
|---|---|
| `main` | ✅ |
| older tags | ❌ |

This is a reference implementation without a release-support commitment. Fixes land on `main`.

## Threat model

Knowing which half of the system owns what avoids reporting things that are out of scope.

**Ory Hydra owns** token issuance, signing keys and their rotation, token introspection and
revocation, and the OAuth2/OIDC protocol surface. Vulnerabilities there belong to
[ory/hydra](https://github.com/ory/hydra).

**This service owns** credential verification, the second factor, session and refresh-token
lifecycle, RBAC decisions, rate limiting and lockout, the login/consent UI it renders, and what
it stores about a user.

### In scope

Authentication bypass, privilege escalation, IDOR, token replay or forgery, injection,
credential disclosure, and anything that lets one user act as another.

### Known limitations, by design

- **`ENV=development` disables the production guards** — debug tracebacks, permissive CORS, an
  auto-generated CSRF secret, and no requirement that the cache and rate limiter be shared. It
  is meant for a laptop. Anything other than the literal string `development` is treated as
  production.
- **The in-memory cache and rate limiter are per-process.** Running more than one replica with
  them silently multiplies every rate limit and breaks pending 2FA challenges. `Settings`
  refuses to boot in that configuration outside development.
- **`SECRET_ENCRYPTION_KEY` is not versioned.** Rotating it makes every stored TOTP seed
  undecryptable and requires re-enrolment. Envelope encryption through a KMS is the right
  answer for a real deployment and is not implemented.
- **Account existence is discoverable** through registration's uniqueness check. Login and
  password reset are deliberately uniform, but registration cannot be without breaking the
  form. Rate limiting is the mitigation.
- **`docker-compose.yaml` runs Hydra with `--dev`**, which relaxes TLS. It is for local use;
  put a real TLS terminator in front of it anywhere else.
