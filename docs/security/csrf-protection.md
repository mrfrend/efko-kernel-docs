# CSRF Protection

## Overview

The gateway uses the **Double Submit Cookie** pattern to protect state-changing requests from browser clients.

- On login, the server sets an `XSRF-TOKEN` cookie (not `httpOnly` — readable by JavaScript)
- Browser clients must read this cookie and send its value in the `X-CSRF-Token` or `X-XSRF-Token` header on every mutating request (`POST`, `PATCH`, `DELETE`)
- The server compares the cookie value against the header value; a mismatch or missing header results in `401 Unauthorized`

Mobile clients do not use cookies and are automatically excluded from CSRF checks.

## How It Works

`CsrfGuard` is applied globally via `APP_GUARD` in `AppModule`:

1. `GET`, `HEAD`, `OPTIONS` — skipped (safe methods)
2. No `XSRF-TOKEN` cookie — skipped (mobile client)
3. `XSRF-TOKEN` cookie present, `X-CSRF-Token` header missing — `401 Unauthorized`
4. Cookie and header values do not match — `401 Unauthorized`
5. Cookie and header match — request passes

## Environment Variables

| Variable | Values | Description |
|---|---|---|
| `CSRF_ENABLED` | `true` / `false` | Enforce CSRF check regardless of `NODE_ENV` |
| `NODE_ENV` | `production` / `development` | CSRF is always enforced in production |

In development, CSRF checks are skipped unless `CSRF_ENABLED=true`.

## Browser Client Integration

```ts
// After login, read the cookie
function getCsrfToken(): string {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('XSRF-TOKEN='))
    ?.split('=')[1] ?? '';
}

// Attach to every mutating request
fetch('/api/v1/personnel/employees', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': getCsrfToken(),
  },
  body: JSON.stringify(payload),
});
```

## Cookie Settings

The `XSRF-TOKEN` cookie is configured in `CookieConfigService`:
- `httpOnly: false` — must be readable by JavaScript
- `sameSite: 'strict'` in production
- Cleared on logout together with the `refreshToken` cookie

## Endpoints

All `POST`, `PATCH`, `DELETE` endpoints require CSRF validation for browser clients. The token is generated and set on `POST /auth/login` and rotated on `POST /auth/refresh-session`.
