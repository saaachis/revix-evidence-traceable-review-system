# 10. Basic authentication for the operations surface

Date: 2026-09-17

## Status

Accepted.

## Context

Proposal section 19 specifies an admin dashboard, authentication-gated, and
treats it as a genuine product surface rather than a debug page. Building it
means introducing two things the project has not had until now: a login, and a
request that writes.

Both deserve a decision rather than a default, because both change claims we
have made elsewhere. The non-functional requirements audit states plainly that
the API is read-only and that there is no authentication because there are no
accounts and nothing to authorise. That was true, and it is the kind of
sentence that quietly becomes false if nobody notices it should have changed.

What actually needs protecting is narrow and worth stating precisely. There are
no user accounts in Revix and there never will be; the proposal puts "user
accounts beyond what admin access requires" explicitly out of scope. The admin
surface has exactly one principal, the operator, and exactly one authorisation
question: is this them. Everything behind the gate is either operational
telemetry or one decision about which vehicle a listing refers to.

The options considered:

1. **No authentication, protected by an unguessable path.** Rejected
   immediately. Obscurity is not a control, and the surface exposes full error
   strings and a write endpoint.
2. **A session cookie with a server-side store.** A login endpoint issues a
   cookie; the API keeps sessions. This is what a product with users would do.
   It also means a session table, expiry, invalidation, and, because the
   browser attaches cookies automatically to cross-origin requests, CSRF
   protection on the one endpoint that writes.
3. **A signed token, exchanged at login and held in the browser.** Lighter than
   a session store, but it is a token service: signing keys, expiry, refresh,
   and a decision about what happens when a key rotates. All of that to
   authenticate one person against one password.
4. **HTTP Basic over HTTPS, compared in constant time.** The credentials travel
   in a header the client sets explicitly on every request.

## Decision

**Option 4.** HTTP Basic authentication, over HTTPS, with both halves of the
credential compared using `secrets.compare_digest`, and both always compared so
the response time does not reveal whether a username exists.

Three details follow from it, and they matter more than the choice itself.

**It fails closed.** If `ADMIN_USERNAME` and `ADMIN_PASSWORD` are not both set,
every admin route answers 503 and none of them touch the database. The
tempting alternative is to leave the surface open when no password is
configured, so it "just works" in development. That is precisely how an
operations console ends up deployed with no password: the behaviour is
identical in both cases, so nothing ever tells you which case you are in. Half
a credential is treated as none, because a deployment that set one and forgot
the other is one where somebody meant to protect this and did not finish.

**The browser sends the credentials, not our server.** The obvious alternative
is for Next to fetch these server-side with the operator credentials in its own
environment. That would put an unauthenticated page in front of an
authenticated API: anybody reaching `/admin` would see the data, because our
server would authenticate on their behalf. Sending the operator's own
credentials from the operator's own browser is what makes the gate mean
anything.

**An explicit header, never a cookie.** The console sets `Authorization`
itself. No cookie is created, so the browser never attaches anything
automatically to a cross-origin request and the entire CSRF class does not
arise on the one endpoint that writes. It also lets CORS keep
`allow_credentials=False`, which is a strictly tighter setting than the
alternative would permit.

## Consequences

**What we accept.** Basic auth sends the credential on every request rather
than exchanging it once, and the console holds it in `sessionStorage` for the
life of the tab, where script in that tab can read it. Over HTTPS, on a surface
with no user-generated content and a strict content security policy, against a
single operator account, that is a proportionate cost. It is written down in
`admin.ts` next to the code so it stays a decision rather than becoming an
oversight.

`sessionStorage` rather than `localStorage` is part of the same trade:
tab-scoped storage dies when the tab closes, so walking away from a shared
machine ends the session, where `localStorage` would persist until somebody
explicitly signed out.

**What changes elsewhere.** The claim that the API is read-only needs
qualifying rather than repeating. The public API is still read-only: every
endpoint outside `/admin` is a GET and CORS permits only GET. There is now one
authenticated write, and the non-functional requirements document says so in
those words.

**What we are not building.** No password reset, no second account, no roles,
no audit log of who did what, because there is one operator and the decisions
recorded are already attributed as `human` in the data itself. If Revix ever
had a second operator, this is the decision to revisit, and the first thing it
would need is the audit trail rather than the roles.

**When to revisit.** A second principal of any kind: another operator, a
service account, or anything reading the admin API that is not a person at a
browser. At that point the authorisation question stops being a boolean and
Basic stops being the right size.
