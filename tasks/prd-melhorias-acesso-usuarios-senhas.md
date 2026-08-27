# PRD: Melhorias de Acesso — Usuários, Senhas e Recuperação

## Introduction

Evoluir o módulo de usuários do Portal BI TMB para cadastro de e-mail de login, alteração de senha (admin e próprio usuário), geração de senha segura, recuperação por link (30 min, uso único), senha provisória administrativa (validade 24h) com troca obrigatória no primeiro acesso, e criação de **novo usuário** com os perfis já existentes (`admin` / `filial`).

Fonte de requisitos: `docs/melhorias_acesso.md` (corrigido: UH13 não cria perfil “Gestão de Entregas”).

Decisões confirmadas:
- Escopo: UH01–UH13 completas.
- E-mails de recuperação/provisória: SMTP padrão operacional (`prb_smtp_settings`).
- Senha provisória: validade **24 horas** fixas.
- Git: permanecer na branch atual (`develop`); **sem commit e sem push** nesta demanda.

## Goals

- Permitir autenticação e recuperação via e-mail de login único e validado.
- Oferecer fluxos seguros de troca de senha (admin, self-service e recuperação).
- Entregar senha provisória por e-mail com bloqueio até definição da senha definitiva.
- Criar novos usuários com perfis existentes, integrando e-mail e senha provisória.
- Manter hash/auditoria/autorização alinhados aos padrões atuais do repositório.

## User Stories

### US-001: Schema — e-mail de login e flags de senha
**Description:** As a developer, I need columns for login email and provisional-password state so credentials flows persist securely.

**Acceptance Criteria:**
- [ ] Migration adds unique (case-insensitive) login email field on users table (nullable allowed initially if needed for legacy rows)
- [ ] Migration adds `must_change_password` (bool, default false) and `temporary_password_expires_at` (timestamptz, nullable)
- [ ] Follow existing `prb_*` / migration naming conventions
- [ ] Tests pass

### US-002: Schema — tokens de recuperação de senha
**Description:** As a developer, I need a password-recovery table storing only token hashes with expiry and single-use status.

**Acceptance Criteria:**
- [ ] Table created (project naming) with user_id, token_hash, created_at, expires_at, used_at, revoked_at, status
- [ ] Status supports Pending / Used / Expired / Revoked (or equivalent)
- [ ] Index/lookup suitable for validating an active token
- [ ] Tests pass

### US-003: Serviço — validação e persistência de e-mail de login
**Description:** As an admin API, I want login email create/update with format, trim, case-insensitive uniqueness.

**Acceptance Criteria:**
- [ ] User create/update accepts login email with trim + format validation
- [ ] Duplicate emails rejected with clear API error
- [ ] Non-admin cannot change another user's login email (backend enforced)
- [ ] Tests pass

### US-004: UI Admin — campo E-mail de Login
**Description:** As an administrator, I want to view/edit login email on the users management screen.

**Acceptance Criteria:**
- [ ] Login email field on user create and edit (Admin React and/or current users UI)
- [ ] Validation errors shown to the user
- [ ] Persistence round-trip works after save
- [ ] Typecheck passes
- [ ] Verify in browser

### US-005: Utilitário — geração de senha segura
**Description:** As the system, I want cryptographically secure password generation meeting policy (upper, lower, digit, special, min length).

**Acceptance Criteria:**
- [ ] Shared helper generates passwords without using user name/email/predictable data
- [ ] Meets documented complexity rules used by the app
- [ ] Unit tests cover charset/length requirements
- [ ] Tests pass

### US-006: Admin — alterar senha de usuário
**Description:** As an administrator, I want to set or auto-generate a new password for a user.

**Acceptance Criteria:**
- [ ] Backend endpoint/action requires admin; stores hash only via existing hasher
- [ ] UI action “Alterar senha” with manual entry and “gerar senha segura”
- [ ] Password never logged or returned in plain text after save (except one-time display if product already does so for admin-set passwords — prefer not to persist plaintext)
- [ ] Typecheck passes
- [ ] Verify in browser

### US-007: Usuário — alterar própria senha
**Description:** As an authenticated user, I want to change my password using current + new + confirm.

**Acceptance Criteria:**
- [ ] Flow under account/settings (or equivalent): current, new, confirm
- [ ] Validates current password and policy; cannot change another user's password
- [ ] Updates hash on success
- [ ] Typecheck passes
- [ ] Verify in browser

### US-008: Recuperação — solicitar reset (anti-enumeração)
**Description:** As a user, I want to request password recovery from login without revealing whether the email exists.

**Acceptance Criteria:**
- [ ] Login UI has “Esqueci minha senha” requesting email
- [ ] Same success message whether email exists or not
- [ ] When email exists: create recovery record, hash token, expiry 30 minutes, revoke prior pending tokens for that user
- [ ] Tests pass

### US-009: Recuperação — e-mail com link (SMTP padrão)
**Description:** As a user, I want a recovery email with a secure link via the operational default SMTP.

**Acceptance Criteria:**
- [ ] Email sent using default `prb_smtp_settings` (not TECH_SMTP)
- [ ] Body includes system id, guidance, link with token only, 30-minute expiry notice; no current password
- [ ] Link path follows app routing (e.g. reset-password?token=...)
- [ ] Tests pass

### US-010: Recuperação — tela de nova senha por token
**Description:** As a user with a valid link, I want to set a new password and invalidate the token.

**Acceptance Criteria:**
- [ ] Page validates token (hash, user, expiry, unused/not revoked)
- [ ] Expired/invalid shows friendly message and blocks change
- [ ] On success: update hash, mark token used, redirect to login
- [ ] Typecheck passes
- [ ] Verify in browser

### US-011: Admin — enviar senha provisória (24h)
**Description:** As an administrator, I want to email a provisional password so the user can first-access the system.

**Acceptance Criteria:**
- [ ] Action “Enviar senha provisória” with confirmation; requires login email present
- [ ] Generates secure password, stores hash, sets must_change_password=true, temporary_password_expires_at=now+24h
- [ ] Email via default SMTP includes provisional password, access link, first-access guidance
- [ ] Re-send invalidates previous provisional window (new hash + new expiry)
- [ ] Typecheck passes
- [ ] Verify in browser

### US-012: Login — gate must_change_password e expiração 24h
**Description:** As the system, I want provisional logins forced into password change and expired provisionals rejected.

**Acceptance Criteria:**
- [ ] Login with expired provisional password fails with clear message
- [ ] Successful provisional login sets session but blocks normal features until password change (only change-password + logout)
- [ ] Backend enforces the gate (not UI-only)
- [ ] Tests pass

### US-013: Primeiro acesso — definir senha definitiva
**Description:** As a user on provisional password, I want to set a definitive password and continue authenticated.

**Acceptance Criteria:**
- [ ] Mandatory screen: new + confirm; must differ from provisional; meets policy
- [ ] On save: update hash, must_change_password=false, clear temporary expiry, audit
- [ ] User remains authenticated when session model allows; redirect to home
- [ ] Typecheck passes
- [ ] Verify in browser

### US-014: Admin — criar novo usuário (sem perfil Gestão de Entregas)
**Description:** As an administrator, I want to create a new user with existing profiles only (`admin`/`filial`), including login email and optional provisional password send.

**Acceptance Criteria:**
- [ ] Create-user flow supports login email and existing profiles only — **no** new “Gestão de Entregas” profile/role
- [ ] Filial profile still requires branch; admin profile follows current rules
- [ ] Optional send provisional password after create when email present
- [ ] Typecheck passes
- [ ] Verify in browser

### US-015: Auditoria e hardening de autorização
**Description:** As security, I want admin password/email/provisional operations audited and backend-authorized without logging secrets.

**Acceptance Criteria:**
- [ ] Audit (existing mechanism) covers admin password change, recovery request, provisional send, self password change, first-access completion
- [ ] Never audit plaintext password or raw token
- [ ] Admin-only operations return 403 for non-admin on API
- [ ] Tests pass

## Functional Requirements

- FR-1: Login email field with trim, format validation, case-insensitive uniqueness.
- FR-2: Only admins may set/change another user's login email or password.
- FR-3: Secure password generator (CSPRNG; upper/lower/digit/special; min length per app policy).
- FR-4: Passwords stored only as existing secure hashes; never in logs, URLs, or cookies.
- FR-5: Self-service password change requires current password + confirmation.
- FR-6: Password recovery via email link; token hashed at rest; 30-minute TTL; single-use; new request revokes prior pending tokens.
- FR-7: Recovery UX must not reveal whether an email is registered.
- FR-8: Recovery and provisional emails use the **default operational SMTP**.
- FR-9: Admin can send provisional password; requires login email; 24h fixed expiry; must_change_password gate.
- FR-10: While must_change_password is true, only password-change and logout are allowed.
- FR-11: After definitive password set, provisional is invalidated and normal access restored.
- FR-12: New users use only existing profiles `admin` and `filial` — do not create “Gestão de Entregas” profile.
- FR-13: After each story, run project checks (tests/typecheck/build equivalent) before the next story.
- FR-14: Implementation stays on branch `develop`; no git commit; no git push.

## Non-Goals

- New profile/role named “Gestão de Entregas” or new granular RBAC matrix.
- Using TECH_SMTP for recovery/provisional emails (unless later ops change).
- Configurable provisional TTL (fixed 24h in this PRD).
- Git commit, push, merge, or new feature branch for this work.
- Rewriting authentication from scratch when existing hash/session can be reused.

## Design Considerations

- Reuse Admin React users screens and existing auth/login patterns.
- Friendly error messages; no stack traces/SQL/tokens in UI.
- Recovery and provisional are separate flows (link vs emailed temporary password).

## Technical Considerations

- Analyze current users table, hash algorithm, sessions, SMTP dispatch, and audit before adding parallel stacks.
- Prefer extending `User` / user service / mailer adapters already in the repo.
- PUBLIC_ORIGIN (or equivalent) for building recovery/login links in emails.
- Streamlit legacy controllers may need parity or clear deprecation if Admin React is the primary admin UI — prefer the primary admin path used in production.

## Success Metrics

- Admin can create user with email and send provisional password end-to-end from VPS SMTP.
- User recovers password via email link within 30 minutes; expired/reused links fail safely.
- Provisional login cannot access app features until definitive password is set.
- No plaintext passwords in DB, logs, or URLs.
- No new profile beyond `admin`/`filial`.

## Open Questions

- Exact min password length if not already centralized — reuse existing policy constant when present.
- Whether Streamlit admin users UI must gain full parity or Admin React alone is sufficient for production.
