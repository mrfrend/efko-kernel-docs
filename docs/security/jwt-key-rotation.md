# JWT Key Rotation Procedure

This document describes the procedure for rotating JWT (JSON Web Token) signing keys in the EFKO Kernel system.

## Overview

The system uses JWT for authentication between the Gateway and backend services. Keys are configured via environment variables:
- `JWT_ACCESS_SECRET` — secret key for signing access tokens
- `JWT_REFRESH_SECRET` — secret key for signing refresh tokens (if implemented)
- `JWT_ACCESS_ISSUER` — issuer identifier for JWT validation

## Why Rotate Keys?

- **Security**: Regular rotation limits the exposure window if a key is compromised
- **Compliance**: Many security standards require periodic key rotation
- **Best Practice**: Industry standard for production systems

## Rotation Strategy

### Option 1: Graceful Rotation with Dual Key Support

This approach allows both old and new keys to be valid during a transition period.

#### Steps:

1. **Generate new keys**
   ```bash
   # Generate 32-byte (256-bit) secret for HS256
   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   ```

2. **Update configuration with dual key support**
   
   Modify JWT configuration to support multiple keys:
   ```typescript
   // In security.module.ts or app.module.ts
   JwtModule.registerAsync({
     secret: process.env.JWT_ACCESS_SECRET,
     signOptions: {
       issuer: process.env.JWT_ACCESS_ISSUER,
     },
     verifyOptions: {
       issuer: process.env.JWT_ACCESS_ISSUER,
       algorithms: ['HS256'],
     },
   })
   ```

3. **Deploy new key to all services simultaneously**
   - Update environment variables for: gateway, auth-service
   - Restart services

4. **Monitor for 1-2 weeks**
   - Watch for authentication failures
   - Check logs for JWT validation errors

5. **Remove old key**
   - Update environment variables to remove old secret
   - Restart services

### Option 2: Immediate Rotation (Recommended for Non-Critical Systems)

This approach is simpler but causes a brief disruption where existing tokens become invalid.

#### Steps:

1. **Generate new key**
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   ```

2. **Update environment variables**
   ```bash
   # Update .env file or deployment secrets
   JWT_ACCESS_SECRET=<new-secret>
   ```

3. **Restart all services**
   ```bash
   # Restart gateway
   nx serve gateway
   
   # Restart auth-service
   nx serve auth-service
   ```

4. **Notify users**
   - Existing sessions will be invalidated
   - Users must re-login

## Pre-Rotation Checklist

- [ ] Generate new secret key(s)
- [ ] Backup current secrets
- [ ] Schedule maintenance window (if using immediate rotation)
- [ ] Prepare rollback plan
- [ ] Notify stakeholders
- [ ] Test new key in staging environment

## Post-Rotation Verification

```bash
# Test authentication with new token
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# Verify token is signed with new key
# Decode JWT at jwt.io to check issuer and structure
```

## Rollback Procedure

If issues occur after rotation:

1. Revert to previous secret in environment variables
2. Restart all services
3. Investigate logs for root cause
4. Retry rotation after fixing issues

## Recommended Rotation Schedule

- **Development**: Rotate every 30 days
- **Staging**: Rotate every 60 days  
- **Production**: Rotate every 90 days

## Key Storage Best Practices

1. **Never commit secrets to git** — use environment variables or secret management
2. **Use strong secrets** — minimum 32 bytes (256 bits) for HS256
3. **Rotate keys regularly** — follow schedule above
4. **Monitor for unauthorized access** — check for unexpected authentication failures
5. **Use different secrets per environment** — dev, staging, production

## Emergency Rotation

If a key is suspected to be compromised:

1. **Immediate rotation** — use Option 2 (immediate rotation)
2. **Investigate logs** — identify when compromise occurred
3. **Notify security team** — if applicable
4. **Review access logs** — identify potentially affected users
5. **Force password reset** — if user credentials may be compromised

## References

- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [NestJS JWT Documentation](https://docs.nestjs.com/security/authentication#jwt-functionality)
